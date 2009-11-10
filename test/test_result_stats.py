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
