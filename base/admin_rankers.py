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
import time
import traceback

from google.appengine.ext import db
from google.appengine.runtime import DeadlineExceededError

from base import decorators
from categories import all_test_sets
from models import result_ranker

import django
from django import http
from django.utils import simplejson

@decorators.admin_required
def UploadRankers(request):
  """Rebuild rankers."""
  time_limit = int(request.REQUEST.get('time_limit', 3))
  data_str = request.REQUEST.get('data')

  if not data_str:
    return http.HttpResponseServerError('Must send "data" param with JSON.')

  try:
    data = simplejson.loads(data_str)

    start_time = time.clock()

    message = None
    updated_rankers = set()
    for (category, test_key, browser, params_str,
         ranker_class, num_scores, values_str) in data:
      if time.clock() - start_time > time_limit:
        message = 'Over time limit'
        break
      test_set = all_test_sets.GetTestSet(category)
      test = test_set.GetTest(test_key)
      ranker = result_ranker.GetOrCreateRanker(test, browser, params_str)
      values = map(int, values_str.split('|'))
      try:
        ranker.SetValues(values, num_scores)
        updated_rankers.add((category, test_key, browser, params_str))
      except db.Timeout:
        pass
      response_params = {
          'updated_rankers': sorted(updated_rankers),
          }
      if message:
        response_params['message'] = message
    return http.HttpResponse(simplejson.dumps(response_params))
  except:
    error = traceback.format_exc()
    return http.HttpResponseServerError(error)
