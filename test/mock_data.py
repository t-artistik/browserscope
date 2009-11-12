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

"""Mock out data structures used by the tests."""

__author__ = 'slamm@google.com (Stephen Lamm)'

from google.appengine.ext import db

from categories import test_set_base
from categories import all_test_sets
from models.user_agent import UserAgent

def GetUserAgentString(firefox_version='3.0.6'):
  return ('Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.6) '
          'Gecko/2009011912 Firefox/%s' % firefox_version)

def GetUserAgent():
  return UserAgent.factory(GetUserAgentString())

UNIT_TEST_UA = {'HTTP_USER_AGENT': 'silly-human', 'REMOTE_ADDR': '127.0.0.1'}


class MockTest(test_set_base.TestBase):
  """Mock test object."""
  def __init__(self, key, min_value, max_value, **kwds):
    test_set_base.TestBase.__init__(
        self,
        key=key,
        name='name for %s' % key,
        url='url for %s' % key,
        doc='doc for %s' % key,
        min_value=min_value,
        max_value=max_value,
        **kwds)


class MockTestSet(test_set_base.TestSet):
  def __init__(self, params=None):
    category = 'mockTestSet'
    tests = (
        MockTest('apple', min_value=0, max_value=1),
        MockTest('banana', min_value=0, max_value=100),
        MockTest('coconut', min_value=0, max_value=1000),
        )
    test_set_base.TestSet.__init__(
        self, category, category, tests, default_params=params)
    all_test_sets.AddTestSet(self)

  def GetTestScoreAndDisplayValue(self, test_key, raw_scores):
    raw_score = raw_scores[test_key]
    score = raw_score * 2
    return score, 'd:%s' % score

  def GetRowScoreAndDisplayValue(self, results):
    score = sum(x['score'] for x in results.values())
    display = str(sum(x['raw_score'] for x in results.values()))
    return score, display
