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

"""Test admin_rankers."""

__author__ = 'slamm@google.com (Stephen Lamm)'


import time
import logging
import unittest

import mock_data
import settings

from django.test.client import Client
from django.utils import simplejson
from google.appengine.ext import db

from models import result_ranker
from third_party import mox

from base import admin_rankers

class TestUploadRankers(unittest.TestCase):
  """Test uploading rankers"""

  def setUp(self):
    self.test_set = mock_data.MockTestSet()

    self.mox = mox.Mox()
    self.mox.StubOutWithMock(time, 'clock')
    self.mox.StubOutWithMock(result_ranker, 'GetOrCreateRanker')
    self.apple_test = self.test_set.GetTest('apple')
    self.coconut_test = self.test_set.GetTest('coconut')
    self.apple_ranker = self.mox.CreateMock(result_ranker.CountRanker)
    self.coconut_ranker = self.mox.CreateMock(result_ranker.LastNRanker)

    self.client = Client()

  def tearDown(self):
    self.mox.UnsetStubs()

  def testBasic(self):
    data = (
        (self.test_set.category, 'apple', 'Firefox 3.0', None,
         'CountRanker', 5, '2|3'),
        (self.test_set.category, 'coconut', 'Firefox 3.0', None,
         'LastNRanker', 7, '101|99|101|2|988|3|101'),
        )
    params = {'data': simplejson.dumps(data),}

    time.clock().AndReturn(0)
    time.clock().AndReturn(0.5)
    result_ranker.GetOrCreateRanker(
        self.apple_test, 'Firefox 3.0', None).AndReturn(self.apple_ranker)
    self.apple_ranker.SetValues([2, 3], 5)
    time.clock().AndReturn(1)  # under timelimit
    result_ranker.GetOrCreateRanker(
        self.coconut_test, 'Firefox 3.0', None).AndReturn(self.coconut_ranker)
    self.coconut_ranker.SetValues([101, 99, 101, 2, 988, 3, 101], 7)

    self.mox.ReplayAll()
    response = self.client.get('/admin/rankers/upload', params)
    self.mox.VerifyAll()
    expected_response_content = simplejson.dumps({
        'updated_rankers': [row[0:4] for row in data]
        })
    self.assertEqual(expected_response_content, response.content)
    self.assertEqual(200, response.status_code)


  def testOverTimeLimit(self):
    data = (
        (self.test_set.category, 'apple', 'Firefox 3.0', None,
         'CountRanker', 5, '2|3'),
        (self.test_set.category, 'coconut', 'Firefox 3.0', None,
         'LastNRanker', 7, '101|99|101|2|988|3|101'),
        )
    params = {'data': simplejson.dumps(data),}

    time.clock().AndReturn(0)
    time.clock().AndReturn(0.5)
    result_ranker.GetOrCreateRanker(
        self.apple_test, 'Firefox 3.0', None).AndReturn(self.apple_ranker)
    self.apple_ranker.SetValues([2, 3], 5)
    time.clock().AndReturn(3.1)  # over timelimit

    self.mox.ReplayAll()
    response = self.client.get('/admin/rankers/upload', params)
    self.mox.VerifyAll()
    expected_response_content = simplejson.dumps({
        'updated_rankers': [data[0][0:4]],
        })
    self.assertEqual(expected_response_content, response.content)
    self.assertEqual(200, response.status_code)
