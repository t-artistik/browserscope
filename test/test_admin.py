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


import datetime
import logging
import unittest

import mock_data
import settings

from django.test.client import Client
from django.utils import simplejson
from google.appengine.ext import db
from models.result import ResultParent
from models.result import ResultTime
from models.user_agent import UserAgent
#from models.user_agent import UserAgentGroup

from base import admin

USER_AGENT_STRINGS = {
    'Firefox 3.0.6': ('Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.6) '
                      'Gecko/2009011912 Firefox/3.0.6'),
    'Firefox 3.5': ('Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.6) '
                    'Gecko/2009011912 Firefox/3.5'),
    'Firefox 3.0.9': ('Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.6) '
                      'Gecko/2009011912 Firefox/3.0.9'),
    }

class TestConfirmUa(unittest.TestCase):
  def setUp(self):
    self.client = Client()
    ua_string = ('Mozilla/5.0 (X11 U Linux armv6l de-DE rv:1.9a6pre) '
                 'Gecko/20080606 '
                 'Firefox/3.0a1 Tablet browser 0.3.7 '
                 'RX-34+RX-44+RX-48_DIABLO_4.2008.23-14')
    self.ua = UserAgent.factory(ua_string)

  def testConfirmBasic(self):
    params = {
        'submit': 1,
        'ac_%s' % self.ua.key(): 'confirm',
        'cht_%s' % self.ua.key(): '',
        'csrf_token': self.client.get('/get_csrf').content,
        }
    response = self.client.get('/admin/confirm-ua', params)
    self.assertEqual(200, response.status_code)
    self.assertTrue(self.ua.get(self.ua.key()).confirmed)


class TestDataDump(unittest.TestCase):
  def setUp(self):
    self.client = Client()

  def tearDown(self):
    db.delete(ResultParent.all(keys_only=True).fetch(1000))
    db.delete(ResultTime.all(keys_only=True).fetch(1000))
    db.delete(UserAgent.all(keys_only=True).fetch(1000))

  def testNoParamsGivesError(self):
    params = {}
    response = self.client.get('/admin/data_dump', params)
    self.assertEqual(400, response.status_code)

  def testNoModelGivesError(self):
    params = {'keys': 'car,home,heart'}
    response = self.client.get('/admin/data_dump', params)
    self.assertEqual(400, response.status_code)

  def testNonExistentKeyIsMarkedLost(self):
    for model in ('ResultParent', 'UserAgent'):
      params = {
          'keys': 'agt1YS1wcm9maWxlcnIRCxIJVXNlckFnZW50GN6JIgw',
          'model': model}
      response = self.client.get('/admin/data_dump', params)
      self.assertEqual(200, response.status_code)
      response_params = simplejson.loads(response.content)
      expected_data = [{
          'model_class': model,
          'lost_key': 'agt1YS1wcm9maWxlcnIRCxIJVXNlckFnZW50GN6JIgw',
          }]
      self.assertEqual(expected_data, response_params['data'])

  def testDumpAll(self):
    test_set = mock_data.MockTestSet()
    keys = []
    for scores in ((1, 4, 50), (1, 1, 20), (0, 2, 30), (1, 0, 10), (1, 3, 10)):
      result = ResultParent.AddResult(
          test_set, '1.2.2.5', mock_data.GetUserAgentString('Firefox 3.5'),
          'apple=%s,banana=%s,coconut=%s' % scores)
      keys.append(str(result.key()))
    params = {
        'model': 'ResultParent',
        'keys': ','.join(keys),
        }
    response = self.client.get('/admin/data_dump', params)
    self.assertEqual(200, response.status_code)
    response_params = simplejson.loads(response.content)
    self.assertEqual(20, len(response_params['data'])) # 5 parents + 15 times


class TestDataDumpKeys(unittest.TestCase):
  def setUp(self):
    self.client = Client()

  def tearDown(self):
    db.delete(ResultParent.all(keys_only=True).fetch(1000))
    db.delete(ResultTime.all(keys_only=True).fetch(1000))
    db.delete(UserAgent.all(keys_only=True).fetch(1000))

  def testCreated(self):
    test_set = mock_data.MockTestSet()
    created_base = datetime.datetime(2009, 9, 9, 9, 9, 0)
    keys = []
    for scores in ((0, 10, 100), (1, 20, 200)):
      ip = '1.2.2.%s' % scores[1]
      result = ResultParent.AddResult(
          test_set, ip, mock_data.GetUserAgentString('Firefox 3.5'),
          'apple=%s,banana=%s,coconut=%s' % scores,
          created=created_base + datetime.timedelta(seconds=scores[1]))
      keys.append(str(result.key()))
    params = {
          'model': 'ResultParent',
          'created': created_base + datetime.timedelta(seconds=15),
          }
    response = self.client.get('/admin/data_dump_keys', params)
    self.assertEqual(200, response.status_code)
    response_params = simplejson.loads(response.content)
    self.assertEqual(None, response_params['bookmark'])
    self.assertEqual(keys[1:], response_params['keys'])

  def testBookmarkRestart(self):
    test_set = mock_data.MockTestSet()
    expected_keys = []
    for scores in ((1, 4, 50), (1, 1, 20), (0, 2, 30), (1, 0, 10), (1, 3, 10)):
      result = ResultParent.AddResult(
          test_set, '1.2.2.5', mock_data.GetUserAgentString('Firefox 3.5'),
          'apple=%s,banana=%s,coconut=%s' % scores)
      expected_keys.append(str(result.key()))
    params = {
        'model': 'ResultParent',
        'fetch_limit': '3'
        }
    response = self.client.get('/admin/data_dump_keys', params)
    keys = []
    self.assertEqual(200, response.status_code)
    response_params = simplejson.loads(response.content)
    self.assertNotEqual(None, response_params['bookmark'])
    keys.extend(response_params['keys'])
    self.assertEqual(3, len(keys))

    del response_params['keys']
    response = self.client.get('/admin/data_dump_keys', response_params)
    self.assertEqual(200, response.status_code)
    response_params = simplejson.loads(response.content)
    self.assertEqual(None, response_params['bookmark'])
    keys.extend(response_params['keys'])
    self.assertEqual(sorted(expected_keys), sorted(keys))

# class TestDataDumpWithMocks(unittest.TestCase):
#   def setUp(self):
#     self.client = Client()
#     self.old_result_parent_get = ResultParent.get

#   def tearDown(self):
#     ResultParent.get = self.old_result_parent_get
#     db.delete(ResultParent.all(keys_only=True).fetch(1000))
#     db.delete(ResultTime.all(keys_only=True).fetch(1000))
#     db.delete(UserAgent.all(keys_only=True).fetch(1000))

#   def testResultParentKeyTimeout(self):
#     test_set = mock_data.MockTestSet()
#     keys = []
#     for scores in ((1, 4, 50), (1, 1, 20), (0, 2, 30), (1, 0, 10), (1, 3, 10)):
#       result = ResultParent.AddResult(
#           test_set, '1.2.2.5', mock_data.GetUserAgentString(),
#           'apple=%s,banana=%s,coconut=%s' % scores)
#       keys.append(result.key())
#     params = {
#         'model': 'ResultParent',
#         'fetch_limit': '4'
#         }

#     self.count = 0
#     def ResultParentGet(cls, *args, **kwds):
#       logging.info('args: %s, kwds: %s', args, kwds)
#       self.count += 1
#       if self.count == 5:
#         raise db.Timeout
#       else:
#         return self.old_result_parent_get(*args, **kwds)
#     ResultParent.get = classmethod(ResultParentGet)

#     response = self.client.get('/admin/data_dump', params)
#     self.assertEqual(200, response.status_code)
#     response_params = simplejson.loads(response.content)
#     self.assertNotEqual(None, response_params['bookmark'])
#     self.assertEqual(12, len(response_params['data'])) # 3 parents + 9 times

#     del response_params['data']
#     response = self.client.get('/admin/data_dump', response_params)
#     self.assertEqual(200, response.status_code)
#     response_params = simplejson.loads(response.content)
#     self.assertEqual(None, response_params['bookmark'])
#     self.assertEqual(8, len(response_params['data'])) # 2 parent + 6 times

  # Exceptions:
  #   Timeouts
  #   - ResultParent keys (first time, after bookmark)
  #   - ResultParent entity
  #   - ResultTime enitities
  #   Past time_limit
