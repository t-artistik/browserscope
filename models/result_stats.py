#!/usr/bin/python2.5
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License')
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared models."""

import re
import logging
import sys

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue

from models.user_agent import UserAgent

BROWSER_NAV = (
  # version_level, label
  ('top', 'Top Browsers'),
  ('0', 'Browser Families'),
  ('1', 'Major Versions'),
  ('2', 'Minor Versions'),
  ('3', 'All Versions')
)

TOP_BROWSERS = (
  'Chrome 2', 'Chrome 3', 'Chrome 4',
  'Firefox 3.0', 'Firefox 3.5',
  'IE 6', 'IE 7', 'IE 8',
  'iPhone 2.2', 'iPhone 3.1',
  'Opera 9.64', 'Opera 10',
  'Safari 3.2', 'Safari 4.0'
)


class BrowserCounter(db.Model):
  """Track the number of results for each category/browsers/version level."""

  category = db.StringProperty()
  browsers = db.StringListProperty()
  count = db.IntegerProperty(default=0, indexed=False)

  @classmethod
  def Increment(cls, category, browsers):
    """Add the browser to the proper version-level groups.

    Add a browser for every version level.
    If a level does not have a string, then use the one from the previous level.
    For example, "Safari 4.3" would increment the following:
        level  browser
            0  Safari
            1  Safari 4
            2  Safari 4.3
            3  Safari 4.3
    Args:
      category: a category string like 'network' or 'reflow'.
      browsers: a list of browsers (e.g. ['Firefox', 'Firefox 3'])
    """
    # TODO(slamm): update memcached stats
    def _IncrementTransaction():
      if len(browsers) < 4:
        browsers.extend(browsers[-1:] * (4 - len(browsers)))
      key_name = cls.KeyName(category, browsers[-1])
      counter = cls.get_by_key_name(key_name)
      if counter is None:
        counter = cls(key_name=key_name,
                      category=category, browsers=browsers)
      counter.count += 1
      counter.put()
    db.run_in_transaction(_IncrementTransaction)

  @classmethod
  def SetCount(cls, category, browsers, count):
    """Set the browser to the proper version-level groups.

    Add a browser for every version level.
    If a level does not have a string, then use the one from the previous level.
    For example, "Safari 4.3" would increment the following:
        level  browser
            0  Safari
            1  Safari 4
            2  Safari 4.3
            3  Safari 4.3
    Args:
      category: a category string like 'network' or 'reflow'.
      browsers: a list of browsers (e.g. ['Firefox', 'Firefox 3'])
      count: an integer
    """
    # TODO(slamm): update memcached stats
    def _SetTransaction():
      if len(browsers) < 4:
        browsers.extend(browsers[-1] * (4 - len(browsers)))
      key_name = cls.KeyName(category, browsers[-1])
      counter = cls.get_by_key_name(key_name)
      if counter:
        if counter.count != count:
          counter.count = count
          counter.put()
      else:
        counter = cls(key_name=key_name, category=category,
                      browsers=browsers, count=count)
        counter.put()
    db.run_in_transaction(_SetTransaction)

  @classmethod
  def GetCounts(cls, category, version_level=None, browsers=None):
    """Get all the browsers for one version level.

    If both version_level and browser are unset, then the 'top' browsers
    are used.

    Args:
      category: a category string like 'network' or 'reflow'.
      version_level (optional): 'top', 0 (family), 1 (major), 2 (minor), 3 (3rd)
      browsers (optional): a list of browsers to use instead of version level
    Returns:
      a dict of browser counts
      e.g. {'Firefox 3.1': 5, 'Safari 4.0': 8, 'Safari 4.5': 3, ...}
    """
    if version_level == 'top' or (version_level is None and browsers is None):
      browsers = TOP_BROWSERS
    if browsers:
      browser_counts = cls.GetCountsByBrowsers(category, browsers)
    else:
      browser_counts = {}
      for counter in cls._GetCounters(category):
        browser = counter.browsers[int(version_level)]
        browser_counts.setdefault(browser, 0)
        browser_counts[browser] += counter.count
    return browser_counts

  @classmethod
  def GetCountsByBrowsers(cls, category, browsers):
    """Get counts for a specific list of browsers.

    Args:
      category: a category string like 'network' or 'reflow'.
      browsers: a list of browsers (e.g. ['Firefox', 'Firefox 3'])
    Returns:
      a dict of browser counts
      e.g. {'Firefox 3.1': 5, 'Safari 4.0': 8, 'Safari 4.5': 3, ...}
    """
    browser_set = set(browsers)
    browser_counts = dict((x, 0) for x in browsers)
    for counter in cls._GetCounters(category):
      browser_match = set(counter.browsers) & browser_set
      if browser_match:
        browser_counts[browser_match.pop()] += counter.count
    return browser_counts

  @classmethod
  def _GetCounters(cls, category):
    query = cls.all().filter('category =', category)
    counters = query.fetch(1000)
    if len(counters) > 900:
      # TODO: Handle more than 1000 user agents strings in a group.
      logging.warn('BrowserCounts(category=%s) will max out at 1000:'
                   ' len(counters)=%s',
                   category, len(counters))
    return counters

  @classmethod
  def KeyName(cls, category, browser):
    return '%s_%s_browser' % (category, browser)


class CategoryStatsManager(object):
  """Manage statistics for a category."""

  @classmethod
  def GetStats(cls, test_set, version_level=None, browsers=None,
               use_memcache=True):
    """Get stats table for a given test_set.

    If version_level and browser are unset, then the 'top' browsers
    are used.

    Args:
      test_set: a TestSet instance
      version_level (optional): 'top', 0, 1, 2, or 3
      browsers (optional): a list of browsers to use instead of version level
      use_memcache: whether to use memcache or not
    Returns:
      {
          browser: {
              'summary_score': summary_score,
              'summary_display': summary_display,
              'total_runs': total_runs,
              'results': {
                  test_key_1: {
                      'raw_score': raw_score_1,
                      'score': score_1,
                      'display': display_1,
                      'expando': expando_1
                      },
                  test_key_2: {...},
                  },
              },
          ...
      }
    """
    stats = {}
    category = test_set.category
    counts = BrowserCounter.GetCounts(category, version_level, browsers)
    if browsers:
      for browser in browsers:
        medians = test_set.GetMedians(browser)
        stats[browser] = test_set.GetStats(medians)
        stats[browser]['total_runs'] = counts[browser]
    return stats
