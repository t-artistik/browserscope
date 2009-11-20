#!/usr/bin/python2.5
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared cron handlers."""

__author__ = 'elsigh@google.com (Lindsey Simon)'


from google.appengine.api import memcache
from google.appengine.ext import db


import django
from django import http

from models import result_stats
from models.result import ResultParent
from models.user_agent import UserAgent

import util
import settings


def UserAgentGroup(request):
  category = request.REQUEST.get('category')
  user_agent_key = db.Key(request.REQUEST.get('user_agent_key'))
  if not category:
    return http.HttpResponse('No cateogry')
  if (category not in settings.CATEGORIES or
      category not in settings.CATEGORIES_BETA):
    return http.HttpResponse('Bad cateogry: %s' % category)
  if not user_agent_key:
    return http.HttpResponse('No key')
  user_agent = UserAgent.get(user_agent_key)
  if user_agent:
    result_stats.UpdateCategory(category, user_agent)
    return http.HttpResponse('Done with UserAgent key=%s' % key)
  else:
    return http.HttpResponse('No user_agent with this key.')


def UpdateRecentTests(request):
  query = db.Query(ResultParent)
  query.order('-created')
  recent_tests = query.fetch(10, 0)

  # need to get the score for a test
  for recent_test in recent_tests:
    score, display = recent_test.get_score_and_display()
    recent_test.score = score
    recent_test.display = display
    recent_test.user_agent_pretty = recent_test.user_agent.pretty()

  memcache.set(key=util.RECENT_TESTS_MEMCACHE_KEY, value=recent_tests,
               time=settings.STATS_MEMCACHE_TIMEOUT)
  return http.HttpResponse('Done')
