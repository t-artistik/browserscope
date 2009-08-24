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

"""Handle administrative tasks for rankers (i.e. median trees)."""

__author__ = 'slamm@google.com (Stephen Lamm)'

import logging
import urllib

from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import datastore
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

import settings
from base import manage_dirty
from base import util
from categories import all_test_sets
from categories import test_set_params
from models import result_ranker
from models.result import ResultParent
from models.user_agent import UserAgent

from third_party.gaefy.db import pager

import django
from django import http
from django.utils import simplejson


def AllRankers(request):
  pass

def AllUserAgents(request):
  pass


def Render(request, template_file, params):
  """Render network test pages."""

  return util.Render(request, template_file, params)


class PagerQuery(pager.PagerQuery):
  def GetBookmark(self, entity):
    """Return a bookmark for the given entity.

    This is handy if you want to start from the middle of a result set.
    """
    return pager.encode_bookmark(self._get_bookmark_values(entity))


MAX_TESTS = 100

def RebuildRankers(request):
  """Rebuild rankers."""
  bookmark = request.GET.get('bookmark')
  category_index = int(request.GET.get('category_index', 0))
  total_results = int(request.GET.get('total_results', 0))
  fetch_limit = int(request.GET.get('fetch_limit', 100))
  offset = int(request.GET.get('offset', 0))

  # Rankers per result_parent <= num_tests_per_category * user_agents_versions
  #            reflow rankers <= 13 * 4 <= 52
  #           network rankers <= 12 * 4 <= 48
  ranker_limit = int(request.GET.get('ranker_limit', 80))
  try:
    if not manage_dirty.UpdateDirtyController.IsPaused():
      manage_dirty.UpdateDirtyController.SetPaused(True)

    category = settings.CATEGORIES[category_index]

    # Query result parents and group by user_agent_pretty
    parent_query = PagerQuery(ResultParent, keys_only=True)
    parent_query.filter('category =', category)
    parent_query.order('user_agent_pretty')
    prev_bookmark, results, next_bookmark = parent_query.fetch(
        fetch_limit, bookmark)
    # Collect the scores: {user_agent_version: [score_1, score_2, ...], ...}
    ranker_scores = {}
    user_agent_versions = {}
    query = db.GqlQuery(
        "SELECT * FROM ResultTime WHERE ANCESTOR IS :1 AND dirty = False")
    test_set = all_test_sets.GetTestSet(category)
    num_tests = len(test_set.tests)
    last_result_parent_key = None
    for result_parent_key in results:
      result_parent = ResultParent.get(result_parent_key)
      user_agent_pretty = result_parent.user_agent_pretty
      if user_agent_pretty not in user_agent_versions:
        user_agent_list = UserAgent.parse_to_string_list(user_agent_pretty)
        user_agent_versions[user_agent_pretty] = user_agent_list
        if len(ranker_scores) + num_tests * len(user_agent_list) > ranker_limit:
          # Processing this result_parent would go over the self-imposed ranker
          # per query limit. Set bookmark with the previous result_parent,
          # because PagerQuery always starts the entity after the bookmark.
          next_bookmark = parent_query.GetBookmark(last_result_parent_key)
          break
      else:
        user_agent_list = user_agent_versions[user_agent_pretty]

      query.bind(result_parent)
      for result_time in query.fetch(MAX_TESTS):
        test_key = result_time.test
        score = result_time.score
        for user_agent_version in user_agent_list:
          ranker_scores.setdefault((user_agent_version, test_key), []).append(
              result_time.score)
      last_result_parent_key = result_parent_key
      total_results += 1

    # Add the scores.
    for (user_agent_version, test_key), scores in ranker_scores.iteritems():
      try:
        test = test_set.GetTest(test_key)
      except KeyError:
        logging.warn('RebuildRankers: test not found: %s', test_key)
        continue
      ranker = result_ranker.ResultRanker.GetOrCreate(
          category, test, user_agent_version,
          result_parent.params_str, ranker_version='next')
      if not bookmark and ranker.TotalRankedScores():
        logging.warn('RebuildRankers: reset ranker: %s', ', '.join(map(str, [
            category, test_key, user_agent_version, result_parent.params_str,
            'ranker_version="next"'])))
        ranker.Reset()
      ranker.Update(scores)

    is_done = False
    if not next_bookmark:
      category_index += 1
      if category_index >= len(settings.CATEGORIES):
        is_done = True
    return http.HttpResponse(simplejson.dumps({
        'is_done': is_done,
        'bookmark': next_bookmark,
        'category_index': category_index,
        'rankers_updated': len(ranker_scores),
        'total_results': total_scores,
        }))
  except DeadlineExceededError:
    logging.warn('DeadlineExceededError in RebuildRankers:'
                 ' bookmark=%s, category=%s, test=%s, user_agent_pretty=%s,'
                 ' total_scores=%s',
                 bookmark, category, test.key, user_agent_pretty,
                 total_scores)
    return http.HttpResponse('RebuildRankers: DeadlineExceededError.',
                             status=403)

def ReleaseNextRankers(request):
  total = int(request.GET.get('total', 0))
  fetch_limit = int(request.GET.get('fetch_limit', 50))
  query = result_ranker.ResultRankerParent.all()
  query.filter('ranker_version =', 'next')
  ranker_parents = query.fetch(fetch_limit)
  for parent in ranker_parents:
    parent.Release()
  num_released = len(ranker_parents)
  total += num_released
  is_done = num_released < fetch_limit
  if is_done:
    manage_dirty.UpdateDirtyController.SetPaused(False)
    datastore.Put(datastore.Entity('ranker migration', name='complete'))
  return http.HttpResponse(simplejson.dumps({
      'is_done': is_done,
      'total': total
      }))


def UpdateResultParents(request):
  bookmark = request.GET.get('bookmark', None)
  total_scanned = int(request.GET.get('total_scanned', 0))
  total_updated = int(request.GET.get('total_updated', 0))
  use_taskqueue = request.GET.get('use_taskqueue', '') == '1'

  query = pager.PagerQuery(ResultParent)
  try:
    prev_bookmark, results, next_bookmark = query.fetch(100, bookmark)
    total_scanned += len(results)
    changed_results = []
    for result in results:
      if hasattr(result, 'user_agent_list') and result.user_agent_list:
        result.user_agent_pretty = result.user_agent_list[-1]
        result.user_agent_list = []
        changed_results.append(result)
      if hasattr(result, 'params') and result.params:
        result.params_str = str(test_set_params.Params(
            [urllib.unquote(x) for x in result.params]))
        result.params = []
        changed_results.append(result)
    if changed_results:
      db.put(changed_results)
      total_updated += len(changed_results)
  except DeadlineExceededError:
    logging.warn('DeadlineExceededError in UpdateResultParents:'
                 ' total_scanned=%s, total_updated=%s.',
                 total_scanned, total_updated)
    return http.HttpResponse('UpdateResultParent: DeadlineExceededError.',
                             status=403)
  if use_taskqueue:
    if next_bookmark:
      taskqueue.Task(
          method='GET',
          url='/admin/update_result_parents',
          params={
              'bookmark': next_bookmark,
              'total_scanned': total_scanned,
              'total_updated': total_updated,
              'use_taskqueue': 1,
              }).add(queue_name='default')
    else:
      logging.info('Finished UpdateResultParents tasks:'
                   ' total_scanned=%s, total_updated=%s',
                   total_scanned, total_updated)
      return http.HttpResponse('UpdateResultParent: Done.')
  return http.HttpResponse(simplejson.dumps({
      'is_done': next_bookmark is None,
      'bookmark': next_bookmark,
      'total_scanned': total_scanned,
      'total_updated': total_updated,
      }))
