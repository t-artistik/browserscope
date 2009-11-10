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

"""Shared Models Unit Tests."""

__author__ = 'elsigh@google.com (Lindsey Simon)'

import unittest
import logging

from models.result import ResultParent

import mock_data

class ResultTest(unittest.TestCase):

  def testGetMedian(self):
    test_set = mock_data.AddFiveResultsAndIncrementAllCounts()

    ranker = test_set.GetTest('testDisplay').GetRanker('Firefox 3')
    self.assertEqual(300, ranker.GetMedian())

    ranker = test_set.GetTest('testVisibility').GetRanker('Firefox 3')
    self.assertEqual(2, ranker.GetMedian())


  def testGetMedianWithParams(self):
    test_set = mock_data.AddThreeResultsWithParamsAndIncrementAllCounts()

    ranker = test_set.GetTest('testDisplay').GetRanker(
        'Firefox 3', str(test_set.default_params))
    self.assertEqual(2, ranker.GetMedian())


  def testAddResult(self):
    parent = mock_data.AddOneTestUsingAddResult()
    expected_results = {
        'testDisplay': 500,
        'testVisibility': 200,
        }
    self.assertEqual(expected_results, parent.GetResults())


  def testAddResultForTestSetWithAdjustResults(self):
    parent = mock_data.AddOneTestUsingAddResultWithAdjustResults()
    self.assertEqual(500, parent.testDisplay)
    self.assertEqual(200, parent.testVisibility)
    expected_results = {
        'testDisplay': 250,
        'testVisibility': 100,
        }
    self.assertEqual(expected_results, parent.GetResults())


  def testAddResultWithExpando(self):
    parent = mock_data.AddOneTestUsingAddResultWithExpando()
    self.assertEqual(20, parent.testDisplay)
    self.assertEqual('testeroo', parent.testVisibility)
    expected_results = {
        'testDisplay': 500,
        'testVisibility': 200,
        }
    self.assertEqual(expected_results, parent.GetResults())

  def testAddResultWithParamsLiteralNoneRaises(self):
    # A params_str with a None value is fine, but not a 'None' string
    test_set = mock_data.MockTestSet('categore')
    ua_string = (
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 6.0; Trident/4.0; '
        'chromeframe; SLCC1; .NET CLR 2.0.5077; 3.0.30729),gzip(gfe),gzip(gfe)')
    self.assertRaises(
        ValueError,
        ResultParent.AddResult, test_set, '12.1.1.1', ua_string,
        'testDisplay=500,testVisibility=200', params_str='None')

  def testGetStatsDataWithParamsEmptyStringRaises(self):
    test_set = mock_data.MockTestSet('categore')
    ua_string = (
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 6.0; Trident/4.0; '
        'chromeframe; SLCC1; .NET CLR 2.0.5077; 3.0.30729),gzip(gfe),gzip(gfe)')
    self.assertRaises(
        ValueError,
        ResultParent.AddResult, test_set, '12.1.1.1', ua_string,
        'testDisplay=500,testVisibility=200', params_str='')


class ChromeFrameAddResultTest(unittest.TestCase):

  def testAddResult(self):
    chrome_ua_string = ('Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) '
                        'AppleWebKit/530.1 (KHTML, like Gecko) '
                        'Chrome/2.0.169.1 Safari/530.1')
    ua_string = (
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 6.0; Trident/4.0; '
        'chromeframe; SLCC1; .NET CLR 2.0.5077; 3.0.30729),gzip(gfe),gzip(gfe)')

    test_set = mock_data.MockTestSet('category-for-chrome-frame-test')
    parent = ResultParent.AddResult(
        test_set, '12.2.2.25', ua_string, 'testDisplay=500,testVisibility=200',
        js_user_agent_string=chrome_ua_string)
    self.assertEqual(chrome_ua_string,
                     parent.user_agent.js_user_agent_string)
