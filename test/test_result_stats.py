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

"""Test Result Stats."""

__author__ = 'slamm@google.com (Stephen Lamm)'

import logging
import unittest

from google.appengine.ext import db
from models import result_stats
from models.result import ResultParent

import mock_data


class BrowserCounterTest(unittest.TestCase):

  def setUp(self):
    db.delete(result_stats.BrowserCounter.all(keys_only=True).fetch(1000))

  def tearDown(self):
    db.delete(result_stats.BrowserCounter.all(keys_only=True).fetch(1000))

  def testEmpty(self):
    self.assertEqual(
        {}, result_stats.BrowserCounter.GetCounts('network', 1))

  def testIncrementOne(self):
    result_stats.BrowserCounter.Increment(
        'cat', ['Firefox', 'Firefox 3', 'Firefox 3.5'])
    self.assertEqual({'Firefox': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 0))
    self.assertEqual({'Firefox 3': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 1))
    self.assertEqual({'Firefox 3.5': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 2))
    self.assertEqual({'Firefox 3.5': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 3))

  def testIncrementMultiple(self):
    result_stats.BrowserCounter.Increment(
        'cat', ['Firefox', 'Firefox 3', 'Firefox 3.5'])
    result_stats.BrowserCounter.Increment(
        'other cat', ['Firefox', 'Firefox 3', 'Firefox 3.5'])
    result_stats.BrowserCounter.Increment(
        'cat', ['Firefox', 'Firefox 3', 'Firefox 3.0', 'Firefox 3.0.7'])
    result_stats.BrowserCounter.Increment(
        'cat', ['Chrome', 'Chrome 4', 'Chrome 4.0', 'Chrome 4.0.32'])
    self.assertEqual({'Firefox': 2, 'Chrome': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 0))
    self.assertEqual({'Firefox 3': 2, 'Chrome 4': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 1))
    self.assertEqual({'Firefox 3.5': 1, 'Firefox 3.0': 1, 'Chrome 4.0': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 2))
    self.assertEqual({'Firefox 3.5': 1, 'Firefox 3.0.7': 1, 'Chrome 4.0.32': 1},
                     result_stats.BrowserCounter.GetCounts('cat', 3))
    self.assertEqual({'Firefox': 1},
                     result_stats.BrowserCounter.GetCounts('other cat', 0))

  def testGetBrowserTotalsTop(self):
    result_stats.BrowserCounter.Increment(
        'cat', ['IE', 'IE 6', 'IE 6.0'])
    result_stats.BrowserCounter.Increment(
        'cat', ['IE', 'IE 6', 'IE 6.1'])
    result_stats.BrowserCounter.Increment(
        'cat', ['Firefox', 'Firefox 3', 'Firefox 3.0', 'Firefox 3.0.7'])
    expected_counts = dict((x, 0) for x in result_stats.TOP_BROWSERS)
    expected_counts['IE 6'] = 2
    expected_counts['Firefox 3.0'] = 1
    self.assertEqual(expected_counts,
                     result_stats.BrowserCounter.GetCounts('cat', 'top'))


  def testSetCount(self):
    result_stats.BrowserCounter.SetCount(
        'cat', ['IE', 'IE 6', 'IE 6.0'], 8)
    self.assertEqual({'IE': 8},
                     result_stats.BrowserCounter.GetCounts('cat', 0))
    # First call creates the db record.
    result_stats.BrowserCounter.SetCount(
        'cat', ['IE', 'IE 6', 'IE 6.0'], 16)
    self.assertEqual({'IE': 16},
                     result_stats.BrowserCounter.GetCounts('cat', 0))



class CategoryStatsManagerTest(unittest.TestCase):

  def setUp(self):
    db.delete(result_stats.BrowserCounter.all(keys_only=True).fetch(1000))

  def tearDown(self):
    db.delete(result_stats.BrowserCounter.all(keys_only=True).fetch(1000))

  def testGetStats(self):
    test_set = mock_data.MockTestSet()
    add_result_params = (
        # ((apple, banana, coconut), firefox_version)
        ((0, 0, 500), '3.0.6'),
        ((1, 1, 200), '3.0.6'),
        ((0, 2, 300), '3.0.6'),
        ((1, 3, 100), '3.5'),
        ((0, 4, 400), '3.5')
        )
    for scores, firefox_version in add_result_params:
      parent = ResultParent.AddResult(
          test_set, '12.2.2.25', mock_data.GetUserAgentString(firefox_version),
          'apple=%s,banana=%s,coconut=%s' % scores)
      parent.increment_all_counts()
    level_1_stats = {
        'Firefox 3': {
            'summary_score': 605,
            'summary_display': '302',
            'total_runs': 5,
            'results': {
                'coconut': {'score': 600, 'raw_score': 300, 'display': 'd:600'},
                'apple': {'score': 1, 'raw_score': 0, 'display': 'no'},
                'banana': {'score': 4, 'raw_score': 2, 'display': 'd:4'}
                }
            }
        }
    self.assertEqual(level_1_stats, result_stats.CategoryStatsManager.GetStats(
        test_set, version_level=1))

    level_3_stats = {
        'Firefox 3.0.6': {
            'summary_score': 603,
            'summary_display': '301',
            'total_runs': 3,
            'results': {
                'coconut': {'score': 600, 'raw_score': 300, 'display': 'd:600'},
                'apple': {'score': 1, 'raw_score': 0, 'display': 'no'},
                'banana': {'score': 2, 'raw_score': 1, 'display': 'd:2'}
                }
            },
        'Firefox 3.5': {
            'summary_score': 818,
            'summary_display': '405',
            'total_runs': 2,
            'results': {
                'coconut': {'score': 800, 'raw_score': 400, 'display': 'd:800'},
                'apple': {'score': 10, 'raw_score': 1, 'display': 'yes'},
                'banana': {'score': 8, 'raw_score': 4, 'display': 'd:8'}
                }
            },
        }
    self.assertEqual(level_3_stats, result_stats.CategoryStatsManager.GetStats(
        test_set, version_level=3))
