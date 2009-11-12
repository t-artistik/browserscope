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

"""Test test_set_base."""

__author__ = 'slamm@google.com (Stephen Lamm)'


import unittest

from categories import test_set_base
import mock_data


class TestParseResults(unittest.TestCase):
  def testValidResultsStringGivesExpectedResults(self):
    results_str = 'apple=1,banana=5,coconut=500'
    expected_results = {
        'apple': {'score': 1},
        'banana': {'score': 5},
        'coconut': {'score': 500},
        }
    test_set = mock_data.MockTestSet()
    results = test_set.ParseResults(results_str)
    self.assertEqual(expected_results, results)


  def testNonIntegerValueRaises(self):
    results_str = 'apple=0,banana=10.00001,coconut=100'
    test_set = mock_data.MockTestSet()
    self.assertRaises(test_set_base.ParseResultsValueError,
                      test_set.ParseResults, results_str)

  def testMissingKeyRaises(self):
    results_str = 'banana=5'
    test_set = mock_data.MockTestSet()
    self.assertRaises(test_set_base.ParseResultsKeyError,
                      test_set.ParseResults, results_str)

  def testKeyTypoRaises(self):
    results_str = 'apple=1,BANANA=10,coconut=2'
    test_set = mock_data.MockTestSet()
    self.assertRaises(test_set_base.ParseResultsKeyError,
                      test_set.ParseResults, results_str)


class TestGetResults(unittest.TestCase):
  def testGetResultsMockData(self):
    results_str = 'apple=1,banana=2,coconut=3'
    test_set = mock_data.MockTestSet()
    expected_results = {
        'apple': {'score': 1},
        'banana': {'score': 2},
        'coconut': {'score': 3},
        }
    self.assertEqual(expected_results, test_set.GetResults(results_str))


class TestGetStats(unittest.TestCase):

  def testGetStatsEmptyRawData(self):
    self.test_set = mock_data.MockTestSet()
    expected_stats = {
        'summary_score': 0,
        'summary_display': '0',
        'results': {},
        }
    self.assertEqual(expected_stats, self.test_set.GetStats({}))

  def testGetStats(self):
    # TODO(slamm): XXX more to do here
    pass


class TestConvert100to10Base(unittest.TestCase):
  def testBasicValues(self):
    Convert100to10Base = test_set_base.TestSet.Convert100to10Base
    self.assertEqual(1, Convert100to10Base(0))
    self.assertEqual(1, Convert100to10Base(4))
    self.assertEqual(1, Convert100to10Base(5))
    self.assertEqual(1, Convert100to10Base(9))
    self.assertEqual(1, Convert100to10Base(10))
    self.assertEqual(1, Convert100to10Base(14))
    self.assertEqual(2, Convert100to10Base(15))
    self.assertEqual(9, Convert100to10Base(90))
    self.assertEqual(9, Convert100to10Base(94))
    self.assertEqual(10, Convert100to10Base(95))
    self.assertEqual(10, Convert100to10Base(100))
