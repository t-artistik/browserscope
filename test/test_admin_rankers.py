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


import unittest

import mock_data

from google.appengine.ext import db

from models import result_ranker
from models.result import ResultParent
from models.result import ResultTime

from base import admin_rankers

class TestResultParentQuery(unittest.TestCase):
  USER_AGENT_PRETTY = 'test_admin_rankers 1.1.1'

  def setUp(self):
    pass

  def tearDown(self):
    db.delete(ResultParent.all(keys_only=True).fetch(1000))
    db.delete(ResultTime.all(keys_only=True).fetch(1000))

  def testQueryEmpty(self):
    limit = 10
    bookmark = None
    query = admin_rankers.ResultParentQuery('el cato', limit, bookmark)
    self.assertFalse(query.HasNext())
    self.assertEqual(None, query.GetNext())
    self.assertEqual(None, query.GetBookmark())
    self.assertEqual(0, query.GetCountUsed())
    self.assertRaises(AssertionError, query.PushBack)

  def testQueryOne(self):
    test_set = mock_data.MockTestSet('el cato')
    result = ResultParent.AddResult(
        test_set, '12.2.2.25', mock_data.GetUserAgentString(),
        'testDisplay=500,testVisibility=200')
    limit = 10
    bookmark = None
    query = admin_rankers.ResultParentQuery(result.category, limit, bookmark)
    self.assert_(query.HasNext())
    self.assertEqual('12.2.2.25', query.GetNext().ip)
    self.assertEqual(None, query.GetBookmark())
    self.assertEqual(1, query.GetCountUsed())
    query.PushBack()
    self.assertEqual(None, query.GetBookmark())
    self.assertEqual(0, query.GetCountUsed())

  def testQueryThree(self):
    test_set = mock_data.MockTestSet('el cato')
    for index in range(3):
      result = ResultParent.AddResult(
          test_set, '12.2.2.%s' % index, mock_data.GetUserAgentString(),
          'testDisplay=500,testVisibility=200')
    limit = 10
    bookmark = None
    query = admin_rankers.ResultParentQuery(result.category, limit, bookmark)
    self.assert_(query.HasNext())
    self.assertEqual('12.2.2.0', query.GetNext().ip)
    self.assert_(query.HasNext())
    self.assertNotEqual(None, query.GetBookmark())
    self.assertEqual(1, query.GetCountUsed())
    self.assertEqual('12.2.2.1', query.GetNext().ip)
    self.assertEqual('12.2.2.2', query.GetNext().ip)
    self.assertFalse(query.HasNext())
    self.assertEqual(3, query.GetCountUsed())
    query.PushBack()
    self.assert_(query.HasNext())
    self.assertEqual(2, query.GetCountUsed())

    bookmark = query.GetBookmark()
    self.assertNotEqual(None, bookmark)
    query = admin_rankers.ResultParentQuery(result.category, limit, bookmark)
    self.assert_(query.HasNext())
    self.assertEqual('12.2.2.2', query.GetNext().ip)


class TestResultTimeQuery(unittest.TestCase):

  def testQueryBasic(self):
    query = admin_rankers.ResultTimeQuery()
    test_set = mock_data.MockTestSet('el cato')
    result = ResultParent.AddResult(
        test_set, '12.2.2.25', mock_data.GetUserAgentString(),
        'testDisplay=500,testVisibility=200')
    for result_time in ResultTime.all().fetch(1000):
      result_time.dirty = False
      result_time.put()
    fetch_limit = 10
    results = query.fetch(fetch_limit, result)
    self.assertEqual([('testDisplay', 500), ('testVisibility', 200)],
                     [(x.test, x.score) for x in results])


class TestRebuildRankers(unittest.TestCase):
  pass

class TestReleaseNextRankers(unittest.TestCase):
  pass
