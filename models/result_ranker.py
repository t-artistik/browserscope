#!/usr/bin/python2.5
#
# Copyright 2008 Google Inc.
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

__author__ = 'slamm@google.com (Stephen Lamm)'

import bisect
import hashlib
import logging

from google.appengine.ext import db


class CountRanker(db.Model):
  """Maintain a list of score counts.

  The minimum score is assumed to be 0.
  The maximum score must be MAX_SCORE or less.
  """
  MIN_SCORE = 0
  MAX_SCORE = 100

  counts = db.ListProperty(long, indexed=False)

  def GetMedianAndNumScores(self):
    median = None
    num_scores = sum(self.counts)
    median_rank = num_scores / 2
    index = 0
    for score, count in enumerate(self.counts):
      median = score
      index += count
      if median_rank < index:
        break
    return median, num_scores

  def Add(self, score):
    if score < self.MIN_SCORE:
      score = self.MIN_SCORE
      logging.warn('CountRanker(key_name=%s) value out of range (%s to %s): %s',
                   self.key().name(), self.MIN_SCORE, self.MAX_SCORE, score)
    elif score > self.MAX_SCORE:
      score = self.MAX_SCORE
      logging.warn('CountRanker(key_name=%s) value out of range (%s to %s): %s',
                   self.key().name(), self.MIN_SCORE, self.MAX_SCORE, score)
    slots_needed = score - len(self.counts) + 1
    if slots_needed > 0:
      self.counts.extend([0] * slots_needed)
    self.counts[score] += 1
    self.put()

  def SetValues(self, counts, num_scores):
    self.counts = counts
    self.put()


class LastNRanker(db.Model):
  """Approximate the median by keeping the last MAX_SCORES scores."""
  MAX_NUM_SAMPLED_SCORES = 100

  scores = db.ListProperty(long, indexed=False)
  num_scores = db.IntegerProperty(default=0, indexed=False)

  def GetMedianAndNumScores(self):
    """Return the median of the last N scores."""
    num_sampled_scores = len(self.scores)
    if num_sampled_scores:
      return self.scores[num_sampled_scores / 2], self.num_scores
    else:
      return None, 0

  def Add(self, score):
    """Add a score into the last N scores.

    If needed, drops the score that is furthest away from the given score.
    """
    num_sampled_scores = len(self.scores)
    if num_sampled_scores < self.MAX_NUM_SAMPLED_SCORES:
      bisect.insort(self.scores, score)
    else:
      index_left = bisect.bisect_left(self.scores, score)
      index_right = bisect.bisect_right(self.scores, score)
      index_center = index_left + (index_right - index_left) / 2
      self.scores.insert(index_left, score)
      if index_center < num_sampled_scores / 2:
        self.scores.pop()
      else:
        self.scores.pop(0)
    self.num_scores += 1
    self.put()

  def SetValues(self, scores, num_scores):
    self.scores = scores
    self.num_scores = num_scores
    self.put()


def RankerKeyName(category, test_key, browser, params_str=None):
  if params_str:
    params_hash = hashlib.md5(params_str).hexdigest()
    return '_'.join((category, test_key, browser, params_hash))
  else:
    return '_'.join((category, test_key, browser))


def RankerClass(min_value, max_value):
  if min_value >= 0 and max_value <= CountRanker.MAX_SCORE:
    return CountRanker
  else:
    return LastNRanker


def GetRanker(test, browser, params_str=None):
  """Get a ranker that matches the given args.

  Args:
    test: an instance of a test_set_base.TestBase derived class.
    browser: a string like 'Firefox 3' or 'Chrome 2.0.156'.
    params_str: a string representation of test_set_params.Params.
  Returns:
    an instance of a RankerBase derived class (None if not found).
  """
  return GetRankers([test], browser, params_str)[0]


def GetRankers(tests, browser, params_str=None):
  """Get a ranker that matches the given args.

  Args:
    tests: a list of instances derived from test_set_base.TestBase.
    browser: a string like 'Firefox 3' or 'Chrome 2.0.156'.
    params_str: a string representation of test_set_params.Params.
  Returns:
    a list of instances derived from RankerBase (None values when not found).
  """
  rankers = [None] * len(tests)
  ranker_specs = {}
  for index, test in enumerate(tests):
    ranker_class = RankerClass(test.min_value, test.max_value)
    ranker_specs.setdefault(ranker_class, ([], []))
    ranker_specs[ranker_class][0].append(index)
    ranker_specs[ranker_class][1].append(RankerKeyName(
        test.test_set.category, test.key, browser, params_str))
  for ranker_class, (indexes, key_names) in ranker_specs.items():
    for index, ranker in zip(indexes, ranker_class.get_by_key_name(key_names)):
      rankers[index] = ranker
  return rankers


def GetOrCreateRanker(test, browser, params_str=None):
  """Get or create a ranker that matches the given args.

  Args:
    test: an instance of a test_set_base.TestBase derived class.
    browser: a string like 'Firefox 3' or 'Chrome 2.0.156'.
    params_str: a string representation of test_set_params.Params.
  Returns:
    an instance of a RankerBase derived class.
  """
  ranker_class = RankerClass(test.min_value, test.max_value)
  return ranker_class.get_or_insert(
      RankerKeyName(test.test_set.category, test.key, browser, params_str))

def GetOrCreateRankers(test, browsers, params_str=None):
  """Get or create a ranker that matches the given args.

  Args:
    test: an instance of a test_set_base.TestBase derived class.
    browsers: a list of browsers like ['Firefox 3', 'Chrome 2.0.156'].
    params_str: a string representation of test_set_params.Params.
  Returns:
    an instance of a RankerBase derived class.
  """
  rankers = []
  ranker_class = RankerClass(test.min_value, test.max_value)
  category, test_key = test.test_set.category, test.key
  key_names = [RankerKeyName(category, test_key, browser, params_str)
               for browser in browsers]
  for key_name, ranker in zip(key_names,
                              ranker_class.get_by_key_name(key_names)):
    if ranker is None:
      rankers.append(ranker_class.get_or_insert(key_name))
    else:
      rankers.append(ranker)
  return rankers
