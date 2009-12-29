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

import array
import bisect
import hashlib
import logging

from google.appengine.api import memcache
from google.appengine.ext import db

class CachedRanker(object):

  MEMCACHE_NAMESPACE = 'result_ranker'

  def CachePut(self):
    memcache.set(self.key().name(), self.ToString(),
                 namespace=self.MEMCACHE_NAMESPACE)
    self.put()

  @classmethod
  def CacheGet(cls, key_names, use_memcache_only=False):
    serialized_rankers = memcache.get_multi(
        key_names, namespace=cls.MEMCACHE_NAMESPACE)
    rankers = dict((k, cls.FromString(k, v))
                   for k, v in serialized_rankers.items())
    logging.info('RANKERS: %s', rankers)
    if not use_memcache_only:
      db_key_names = [k for k in key_names if k not in rankers]
      if db_key_names:
        for key_name, ranker in zip(db_key_names,
                                    cls.get_by_key_name(db_key_names)):
          if ranker:
            rankers[key_name] = ranker
    return rankers

  def key(self):
    raise NotImplementedError

  def put(self):
    raise NotImplementedError

  @classmethod
  def get_by_key_name(cls, key_names):
     raise NotImplementedError

  def ToString(self):
    raise NotImplementedError

  @classmethod
  def FromString(cls, key_name, serialized_value):
    raise NotImplementedError


class CountRanker(db.Model, CachedRanker):
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
    self.CachePut()

  def SetValues(self, counts, num_scores):
    self.counts = counts
    self.CachePut()

  def ToString(self):
    return array.array('L', self.counts).tostring()

  @classmethod
  def FromString(cls, key_name, value_str):
    counts = array.array('L')
    counts.fromstring(value_str)
    return cls(key_name=key_name, counts=counts.tolist())


class LastNRanker(db.Model, CachedRanker):
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
    self.CachePut()

  def SetValues(self, scores, num_scores):
    self.scores = scores
    self.num_scores = num_scores
    self.CachePut()

  def ToString(self):
    return array.array('l', self.scores + [self.num_scores]).tostring()

  @classmethod
  def FromString(cls, key_name, value_str):
    scores = array.array('l')
    scores.fromstring(value_str)
    num_scores = scores.pop()
    return cls(key_name=key_name, scores=scores.tolist(), num_scores=num_scores)


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
  ranker_class = RankerClass(test.min_value, test.max_value)
  category = test.test_set.category
  key_name = RankerKeyName(category, test.key, browser, params_str)
  return ranker_class.CacheGet([key_name]).get(key_name, None)


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
  key_name_indexes = {}
  ranker_key_names = {}
  for index, test in enumerate(tests):
    category = test.test_set.category
    key_name = RankerKeyName(category, test.key, browser, params_str)
    key_name_indexes[key_name] = index
    ranker_class = RankerClass(test.min_value, test.max_value)
    ranker_key_names.setdefault(ranker_class, []).append(key_name)
  for ranker_class, key_names in ranker_key_names.items():
    for key_name, ranker in ranker_class.CacheGet(key_names).items():
      rankers[key_name_indexes[key_name]] = ranker
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
  category = test.test_set.category
  key_name = RankerKeyName(category, test.key, browser, params_str)
  ranker = ranker_class.CacheGet(
      [key_name], use_memcache_only=True).get(key_name, None)
  if not ranker:
    ranker = ranker_class.get_or_insert(key_name)
  return ranker


def GetOrCreateRankers(test, browsers, params_str=None):
  """Get or create a ranker that matches the given args.

  Args:
    test: an instance of a test_set_base.TestBase derived class.
    browsers: a list of browsers like ['Firefox 3', 'Chrome 2.0.156'].
    params_str: a string representation of test_set_params.Params.
  Returns:
    [browser_ranker_1, browser_ranker_2, ...]
  """
  rankers = []
  ranker_class = RankerClass(test.min_value, test.max_value)
  category = test.test_set.category
  key_names = [RankerKeyName(category, test.key, browser, params_str)
               for browser in browsers]
  existing_rankers = ranker_class.CacheGet(key_names)
  for key_name in key_names:
    ranker = existing_rankers.get(key_name, None)
    if not ranker:
      ranker = ranker_class.get_or_insert(key_name)
    rankers.append(ranker)
  return rankers
