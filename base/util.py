#!/usr/bin/python2.4
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

"""Shared utility functions."""

__author__ = 'elsigh@google.com (Lindsey Simon)'

import hashlib
import logging
import random
import re
import sys
import urllib

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue

import django
from django import http
from django import shortcuts
from django.template import loader, Context

from django.template import add_to_builtins
add_to_builtins('base.custom_filters')

import settings

from models.result import *
from models.user_agent import *
from categories import all_test_sets
from categories import test_set_params
from base import decorators
from base import manage_dirty


#@decorators.trusted_tester_required
def Render(request, template, params={}, category=None):
  """Wrapper function to render templates with global and category vars."""

  params['app_title'] = settings.APP_TITLE
  params['app_categories'] = []
  params['is_admin'] = users.is_current_user_admin()
  #http://code.google.com/appengine/docs/python/users/userclass.html#User_user_id
  current_user = users.get_current_user()
  if current_user:
    params['user_id'] = current_user.user_id()
    params['is_elsigh'] = current_user.nickname() == 'elsigh'
  else:
    params['is_elsigh'] = False
    params['user_id'] = None
  params['sign_in'] = users.create_login_url(request.get_full_path())
  params['sign_out'] = users.create_logout_url('/')

  # Creates a list of tuples categories and their ui names.
  for i, test_set in enumerate(all_test_sets.GetTestSets()):
    params['app_categories'].append([test_set.category, test_set.category_name])
    # Select the current page's category.
    if category and category == test_set.category:
      params['app_category'] = test_set.category
      params['app_category_index'] = i

  if category != None:
    template = '%s/%s' % (category, template)
  return shortcuts.render_to_response(template, params)


def GetServer(request):
  """A utility function for getting the server and port."""
  server = request.META['SERVER_NAME']
  server_port = request.META['SERVER_PORT']
  if server_port != '80':
    server = server + ':' + server_port
  return server


RECENT_TESTS_MEMCACHE_KEY = 'recent_tests'
def Home(request):
  """Our Home page."""

  # If we don't find anything in memcache, we just won't show the recent
  # tests on the homepage. Should happen VERY rarely.
  recent_tests = memcache.get(key=RECENT_TESTS_MEMCACHE_KEY)
  if not recent_tests:
    ScheduleRecentTestsUpdate()

  stats_tables = {}
  intro_text = {}
  for test_set in all_test_sets.GetTestSets():
    stats_tables[test_set.category] = GetStats(request, test_set, output='html')
    intro_text[test_set.category] = test_set.home_intro

  message = request.GET.get('message')

  params = {
    'page_title': 'Home',
    'stats_tables': stats_tables,
    'intro_text': intro_text,
    'recent_tests': recent_tests,
    'message': message
  }
  return Render(request, 'home.html', params)


def Faq(request):
  """FAQ"""
  params = {
    'page_title': 'FAQ',
    'section_urls': ''
  }
  return Render(request, 'faq.html', params)


def AllTests(request):
  """All Tests"""
  params = {
    'page_title': 'All Tests',
    'section_urls': ''
  }
  return Render(request, 'alltests.html', params)


def Results(request):
  """Results"""
  params = {
    'page_title': 'Results',
    'section_urls': ''
  }
  return Render(request, 'results.html', params)


def Contribute(request):
  """Contribute"""
  params = {
    'page_title': 'Contribute',
    'section_urls': ''
  }
  return Render(request, 'contribute.html', params)


def CheckThrottleIpAddress(ip):
  """Will check for over-zealous beacon abusers and bots."""
  return True


@decorators.admin_required
def ClearMemcache(request):
  message = []

  continue_url = request.GET.get('continue')

  recent = request.GET.get('recent')
  if recent:
    memcache.delete(key=RECENT_TESTS_MEMCACHE_KEY, seconds=0)
    message.append('Cleared memcache for recent tests')

  category = request.GET.get('category')
  if category:
    categories = category.split(',')
  else:
    categories = settings.CATEGORIES

  ua = request.GET.get('ua')
  version_level = request.GET.get('v')
  if ua:
    user_agent_strings = ua.split(',')
  elif version_level:
    user_agent_strings = UserAgentGroup.GetStrings(version_level)
  else:
    return http.HttpResponse('Either pass in ua= or v=')

  logging.info('categories are: %s' % categories)
  logging.info('user_agent_strings are: %s' % user_agent_strings)
  for category in categories:
    for user_agent in user_agent_strings:
      memcache_ua_key = '%s_%s' % (category, user_agent)
      memcache.delete(key=memcache_ua_key, seconds=0,
                      namespace=settings.STATS_MEMCACHE_UA_ROW_NS)
      logging.info('Deleting %s in memcache' % memcache_ua_key)

  message.append('Cleared memcache for categories: %s and '
                 'user_agent_strings: %s' % (categories, user_agent_strings))

  if continue_url:
    if not re.search('\?', continue_url):
      continue_url += '?'
    continue_url += '&message=' + urllib.quote(' '.join(message))
    return http.HttpResponseRedirect(continue_url)
  else:
   return http.HttpResponse('<br>'.join(message))


def ScheduleRecentTestsUpdate():
  try:
    taskqueue.Task(method='GET').add(queue_name='recent-tests')
  except:
    logging.info('Cannot add task: %s:%s' % (sys.exc_type, sys.exc_value))


BAD_BEACON_MSG = 'Nein swine.'
BEACON_COMPLETE_CB_RESPONSE = 'BEACON_COMPLETE = 1;'
@decorators.check_csrf
def Beacon(request):
  """Records result times in the datastore.
  This is the handler for after a test is done.
  ex: /beacon?category=reflow&csrf_token=number&results=tes1=150,test2=300
  """
  # First make sure this IP is not being an overachiever ;)
  ip = request.META.get('REMOTE_ADDR')
  if not CheckThrottleIpAddress(ip):
    return http.HttpResponseServerError(BAD_BEACON_MSG)
  # Mask the IP for storage
  ip_hash = hashlib.md5(ip).hexdigest()

  callback = request.GET.get('callback')
  category = request.GET.get('category')
  results_str = request.GET.get('results')
  params_str = request.GET.get('params')
  user_agent_string = request.META.get('HTTP_USER_AGENT')

  if not category or not results_str:
    logging.debug('Got no category or results.')
    return http.HttpResponse(BAD_BEACON_MSG)
  if not all_test_sets.HasTestSet(category):
    logging.warn('Could not get a test_set for category: %s' % category)
    return http.HttpResponse(BAD_BEACON_MSG)

  test_set = all_test_sets.GetTestSet(category)

  optional_fields = {}
  if params_str:
    optional_fields['params_str'] = urllib.unquote(params_str)
    #logging.info('Beacon params: %s' % optional_fields['params_str'])
  optional_fields['user'] = users.get_current_user()

  result_parent = ResultParent.AddResult(
      test_set, ip_hash, user_agent_string, results_str, **optional_fields)
  if not result_parent:
    return http.HttpResponse(BAD_BEACON_MSG)

  manage_dirty.ScheduleDirtyUpdate()
  ScheduleRecentTestsUpdate()

  if callback:
    return http.HttpResponse(BEACON_COMPLETE_CB_RESPONSE)
  else:
    # Return a successful empty 204.
    return http.HttpResponse('', status=204)


@decorators.dev_appserver_only
@decorators.provide_csrf
def GetCsrf(request):
  """A get request to return a CSRF token."""
  csrf_token = request.session['csrf_token']
  return_csrf = request.GET.get('return_csrf', True)
  if return_csrf != '0':
    msg = csrf_token
  else:
    if csrf_token:
      msg = 'True'
    else:
      msg = 'False'
  return http.HttpResponse(msg)


def GetStats(request, test_set, output='html', opt_tests=None,
             use_memcache=True):
  """Returns the stats table.
  Args:
    request: a request object.
    test_set: a TestSet instance.
    output: Output type html or else you get a dict of params.
    opt_tests: list of tests.
    use_memcache: Use memcache or not.
  """
  version_level = request.GET.get('v', 'top')
  user_agent_strings = UserAgentGroup.GetStrings(version_level)

  tests = [test for test in opt_tests or test_set.tests
           if not hasattr(test, 'is_hidden_stat') or not test.is_hidden_stat]
  params_str = None
  if test_set.default_params:
    params_str = str(test_set.default_params)
  stats = GetStatsData(test_set.category, tests, user_agent_strings,
                       params_str, use_memcache, version_level)
  # Looks for a category_results=test1=X,test2=X url GET param.
  results = None
  results_str = request.GET.get('%s_results' % test_set.category)
  if results_str:
    results = dict((x['key'], x) for x in test_set.ParseResults(results_str))

  # Set current_ua_string to one in user_agent_strings
  current_ua = UserAgent.factory(request.META['HTTP_USER_AGENT'])
  current_ua_string = current_ua.pretty()
  for ua_string in user_agent_strings:
    if current_ua_string.startswith(ua_string):
      current_ua_string = ua_string
      break
  else:
    # current_ua_string was not found in user_agent_strings.
    if results:
      user_agent_strings.append(current_ua_string)
      user_agent_strings.sort()

  # Adds the current results into the stats dict.
  if results:
    stats.setdefault(current_ua_string, {})
    stats[current_ua_string]['current_results'] = {}
    current_ua_score = 0
    for test in tests:
      if test.key in results:
        result = results[test.key]
        median = result['score'] or ''
        score, display, ua_score = GetScoreAndDisplayValue(test, median)
        stats[current_ua_string]['current_results'][test.key] = {
            'median': median,
            'score': score,
            'display': display,
            'expando': result.get('expando', None),
            }
        current_ua_score += ua_score
    stats[current_ua_string]['current_score'] = current_ua_score / len(tests)

  params = {
    'category': test_set.category,
    'tests': tests,
    'v': version_level,
    'user_agents': user_agent_strings,
    'request_path': request.path,
    'current_user_agent': current_ua_string,
    'stats': stats,
    'params': test_set.default_params,
  }
  #logging.info("PARAMS: %s", str(params))
  if output is 'html':
    return GetStatsTableHtml(params)
  else:
    return params


def GetStatsData(category, tests, user_agents, params_str, use_memcache=True,
                 version_level='top'):
  stats = {}
  for user_agent in user_agents:
    user_agent_stats = None
    if use_memcache:
      memcache_ua_key = '%s_%s' % (category, user_agent)
      user_agent_stats = memcache.get(
          key=memcache_ua_key, namespace=settings.STATS_MEMCACHE_UA_ROW_NS)
    if not user_agent_stats:
      total_runs = None
      user_agent_results = {}
      user_agent_score = 0
      for test in tests:
        ranker = test.GetRanker(user_agent, params_str)
        if ranker:
          median, total_runs = ranker.GetMedianAndNumScores(
            num_scores=total_runs)
        else:
          median, total_runs = None, 0
          logging.warn("GetStatsData: Ranker not found: %s, %s, %s, %s",
                       category, test.key, user_agent, params_str)
        if median is None:
          median = ''
        score, display, ua_score = GetScoreAndDisplayValue(test, median)
        user_agent_score += ua_score
        user_agent_results[test.key] = {
            'median': median,
            'score': score,
            'display': display,
            }
      user_agent_stats = {
          'total_runs': total_runs,
          'results': user_agent_results,
          'score': user_agent_score / len(tests)
          }
      if use_memcache:
        memcache.set(key=memcache_ua_key, value=user_agent_stats,
                     time=settings.STATS_MEMCACHE_TIMEOUT,
                     namespace=settings.STATS_MEMCACHE_UA_ROW_NS)
    if version_level == 'top' or user_agent_stats['total_runs']:
      # TODO(slamm): double check what this code needs to do
      stats[user_agent] = user_agent_stats
  return stats


def GetScoreAndDisplayValue(test, median):
  # Score for the template classnames is a value of 0-10.
  if test.score_type == 'boolean':
    # Boolean scores are 1 or 10.
    if median == 0:
      score = 1
      display = settings.STATS_SCORE_FALSE
    else:
      score = 10
      display = settings.STATS_SCORE_TRUE
  elif test.score_type == 'custom':
    # The custom_tests_function returns a score between 1-100 which we'll
    # turn into a 0-10 display.
    score, display = test.GetScoreAndDisplayValue(median)
    score = int(round(float('%s.0' % int(score)) / 10))
    #logging.info('got display:%s, score:%s for %s w/ median: %s' %
    #             (display, score, test.key, median))

  # Normalize very low scores per test for calculating an overall score for
  # the user agent.
  ua_score = score
  if ua_score < 5:
    ua_score = 5
  return score, display, ua_score


def GetStatsTableHtml(params):
  """Returns the HTML of the stats table.

  Args:
    params: Example:
            params = {
              'v': one of the keys in BROWSER_NAV,
              'current_user_agent': a user agent entity,
              'user_agents': list_of user agents,
              'tests': list of test names,
              'stats': dict - stats[test_name][user_agent],
              'total_runs': total_runs[test_name],
              'request_path': request.path,
              'params': result_parent.params, #optional
            }

  """
  params['browser_nav'] = BROWSER_NAV
  params['is_admin'] = users.is_current_user_admin()
  if not re.search('\?', params['request_path']):
    params['request_path'] = params['request_path'] + '?'
  t = loader.get_template('stats_table.html')
  html = t.render(Context(params))
  return html


@decorators.dev_appserver_only
@decorators.admin_required
def SeedDatastore(request):
  """Seed Datastore."""

  NUM_RECORDS = 3
  increment_counts = request.GET.get('increment_counts', True)
  if increment_counts == '0':
    increment_counts = False

  def _GetRandomScore(test):
    return random.randrange(test.min_value, test.max_value + 1)

  for test_set in all_test_sets.GetTestSets():
    for user_agent_string in TOP_USER_AGENT_STRINGS:
      for _ in range(NUM_RECORDS):
        results_str = ','.join(['%s=%s' % (test.key, _GetRandomScore(test))
                               for test in test_set.tests])
        params_str = None
        if test_set.default_params:
          params_str = str(test_set.default_params)
        result_parent = ResultParent.AddResult(
            test_set, '1.2.3.4', user_agent_string, results_str, params_str)
        if increment_counts:
          result_parent.increment_all_counts()
  return http.HttpResponseRedirect('?datastore_seeded')


@decorators.admin_required
def UpdateDatastore(request):
  """Generic datastore munging routine."""

  # user_agent = UserAgent.factory(TOP_USER_AGENT_STRINGS[0])
  # query = db.Query(TestTime)
  # test_times = query.fetch(1000, 0)
  # for test_time in test_times:
  #   test_time.user_agent = user_agent
  #   test_time.put()
  # return http.HttpResponse('All Done')

  query = db.Query(UserAgent)
  key = request.GET.get('key')
  if key:
    query.filter('__key__ >', db.Key(key))
  query.order('__key__')
  record = query.get()
  if not record:
    return http.HttpResponse('All Done!')

  record.update_groups()

  params = {
    'next_url': '/update_datastore?key=%s' % record.key(),
    'current_name': record.get_string_list(),
    'next_name': 'nextosity'
  }
  return Render(request, 'update_datastore.html', params)


@decorators.admin_required
def ClearDatastore(request):
  """Clears data in the datastore, many at a time (for admins only)."""
  clear = (None, 'None')
  atatime = 10

  msg = ''
  query = db.Query(clear[0])
  rows = query.fetch(atatime)
  length = len(rows)
  if length is 0:
    msg += 'No more rows to delete<br>'
  else:
    msg += 'Deleting %s %s<br>' % (length, clear[1])
    db.delete(rows)
    query = db.Query(clear[0])
    more = query.fetch(1)
    if len(more) is not 0:
      msg += 'Now do it again!'
      msg += '<script>window.location.href="/reflows/clear_datastore";</script>'
  return http.HttpResponse(msg)


@decorators.dev_appserver_only
@decorators.check_csrf
def FakeCheckCsrf(request):
  return http.HttpResponse('yo')


def UserAgents(request):
  user_agents = UserAgent.all().fetch(1000)
  ua_csv = '\n'.join(
    ['%s,%s,"%s"' % (x.pretty(), x.key().id_or_name(), x.string)
     for x in user_agents])
  return http.HttpResponse(ua_csv, mimetype="text/csv")
