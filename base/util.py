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

"""Shared utility functions."""

__author__ = 'elsigh@google.com (Lindsey Simon)'

import hashlib
import logging
import random
import os
import pickle
import re
import sys
import time
import urllib

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.api import urlfetch

import django
from django import http
from django import shortcuts
from django.template import loader, Context

from django.template import add_to_builtins
add_to_builtins('base.custom_filters')

import settings

from models import result_stats
from models.result import *
from models.user_agent import *
from categories import all_test_sets
from categories import test_set_params
from base import decorators
from base import manage_dirty


TEST_DRIVER_TPL = 'test_driver.html'


#@decorators.trusted_tester_required
def Render(request, template, params={}, category=None):
  """Wrapper function to render templates with global and category vars."""
  params['app_title'] = settings.APP_TITLE
  params['version_id'] = os.environ['CURRENT_VERSION_ID']
  params['build'] = settings.BUILD
  params['epoch'] = int(time.time())
  params['request_path'] = request.get_full_path()
  params['request_path_lastbit'] = re.sub('^.+\/([^\/]+$)', '\\1', request.path)
  params['current_ua_string'] = request.META['HTTP_USER_AGENT']
  params['current_ua'] = UserAgent.factory(params['current_ua_string']).pretty()
  params['chromeframe_enabled'] = request.COOKIES.get(
      'browserscope-chromeframe-enabled', '0')
  params['app_categories'] = []
  params['is_admin'] = users.is_current_user_admin()

  current_user = users.get_current_user()
  if current_user:
    params['user_id'] = current_user.user_id()
    params['is_elsigh'] = current_user.nickname() == 'elsigh'
  else:
    params['user_id'] = None
    params['is_elsigh'] = False
  params['user'] = current_user

  params['sign_in'] = users.create_login_url(request.get_full_path())
  params['sign_out'] = users.create_logout_url('/')

  # Creates a list of tuples categories and their ui names.
  for i, test_set in enumerate(all_test_sets.GetTestSets()):
    params['app_categories'].append([test_set.category, test_set.category_name])
    # Select the current page's category.
    if category and category == test_set.category:
      params['app_category'] = test_set.category
      params['app_category_name'] = test_set.category_name
      params['app_category_index'] = i

  if category != None and template != TEST_DRIVER_TPL:
    template = '%s/%s' % (category, template)

  return shortcuts.render_to_response(template, params)



def CategoryTest(request):
  """Loads the test frameset for a category."""
  category = re.sub('\/test.*', '', request.path)[1:]
  test_set = all_test_sets.GetTestSet(category)
  params = {
    'category': test_set.category,
    'page_title': '%s - Tests' % test_set.category_name,
    'continue': request.GET.get('continue', ''),
    'autorun': request.GET.get('autorun', ''),
    'test_page': test_set.test_page
  }
  #return shortcuts.render_to_response('test_frameset.html', params)
  return Render(request, 'test_frameset.html', params)


@decorators.provide_csrf
def CategoryTestDriver(request):
  """Loads the test driver for a category."""
  category = request.GET.get('category')
  test_set = all_test_sets.GetTestSet(category)
  params = {
    'category': test_set.category,
    'page_title': '%s - Test Driver' % test_set.category_name,
    'continue': request.GET.get('continue', ''),
    'autorun': request.GET.get('autorun', ''),
    'test_page': test_set.test_page,
    'csrf_token': request.session.get('csrf_token'),
    'hide_footer': True
  }
  return Render(request, TEST_DRIVER_TPL, params, category)


def GetServer(request):
  """A utility function for getting the server and port."""
  server = request.META['SERVER_NAME']
  server_port = request.META['SERVER_PORT']
  if server_port != '80':
    server = server + ':' + server_port
  return server

STATIC_MESSAGE = ('<em class="rt-static">This is a recent snapshot '
                  'of the results - '
                  'it will be refreshed every hour.</em>')
RECENT_TESTS_MEMCACHE_KEY = 'recent_tests'
def Home(request):
  """Our Home page."""

  recent_tests = memcache.get(key=RECENT_TESTS_MEMCACHE_KEY)
  if not recent_tests:
    ScheduleRecentTestsUpdate()

  results_params = []
  for category in settings.CATEGORIES:
    results_uri_string = request.GET.get('%s_results' % category)
    if results_uri_string:
      results_params.append('%s_results=%s' % (category, results_uri_string))

  stats_tables = {}
  test_set = None
  category = request.GET.get('category')
  if category:
    test_set = all_test_sets.GetTestSet(category)
  else:
    if len(results_params) > 0:
      for category in settings.CATEGORIES:
        if request.GET.get('%s_results' % category):
          test_set = all_test_sets.GetTestSet(category)
          break
  # If we still got no test_set, take the first one in settings.CATEGORIES
  if not test_set:
    category = settings.CATEGORIES[0]
    test_set = all_test_sets.GetTestSet(category)

  # Tell GetStats what to output.
  output = request.GET.get('o', 'html')
  if output not in ['pickle', 'xhr', 'html', 'csv']:
    return http.HttpResponse('Invalid output specified')
  stats_table = GetStats(request, test_set, output)

  # Show a static message above the table.
  if category in settings.STATIC_CATEGORIES and output in ['xhr', 'html']:
    stats_table = '%s%s' % (STATIC_MESSAGE, stats_table)

  if output in ['xhr', 'pickle', 'csv']:
    return http.HttpResponse(stats_table)
  else:
    params = {
      'page_title': 'Home',
      'results_params': '&'.join(results_params),
      'stats_table_category': test_set.category,
      'stats_table': stats_table,
      'recent_tests': recent_tests,
      'message': request.GET.get('message'),
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


IP_THROTTLE_NS = 'IPTHROTTLE'
def CheckThrottleIpAddress(ip, user_agent_string):
  """Prevent beacon abuse.
  This throttle allows you to "RunAllTests" 10 times per day per IP and
  major browser. i.e. the key is something like 1.1.1.1_Opera 10

  We only use memcache here, so if we allow some extras in b/c of that, phooey.

  Args:
    ip: A masked IP address string.
    user_agent_string: A user agent string.
  Returns:
    A Boolean, True if things are aok, False otherwise.
  """

  key = '%s_%s' % (ip, user_agent_string)
  timeout = 86400 # 60 * 60 * 24
  runs_per_timeout = 10

  runs = memcache.get(key, IP_THROTTLE_NS)
  #logging.info('CheckThrottleIpAddress runs: %s' % runs)
  if runs is None:
    memcache.set(key=key, value=1, time=60, namespace=IP_THROTTLE_NS)
  elif runs <= runs_per_timeout:
    memcache.incr(key=key, delta=1,namespace=IP_THROTTLE_NS)
  else:
    return False
  return True


@decorators.admin_required
def ShowMemcache(request):
  stats = memcache.get_stats()
  response = '<h1>Memcache Stats</h1>'
  for key, val in stats.items():
    response += '<h2>%s: %s</h2>' % (key, val)
  return http.HttpResponse(response)


@decorators.admin_required
def ClearMemcache(request):
  message = []
  continue_url = request.GET.get('continue')

  # KABOOM
  if request.GET.get('all'):
    memcache.flush_all()
    message.append('Cleared memcache for all keys.')

  # Piecemeal cleanups
  else:
    recent = request.GET.get('recent')
    if recent:
      memcache.delete(RECENT_TESTS_MEMCACHE_KEY)
      message.append('Cleared memcache for recent tests.')

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
      # TODO(slamm): XXX clear memcache properly
      user_agent_strings = [] # UserAgentGroup.GetStrings(version_level)
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

  # All done.
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
    #logging.info('ScheduleRecentTestsUpdate made a task')
  except:
    logging.info('Cannot add task: %s:%s' % (sys.exc_type, sys.exc_value))


BAD_BEACON_MSG = 'Error in Beacon: '
BEACON_COMPLETE_CB_RESPONSE = 'BEACON_COMPLETE = 1;'
@decorators.check_csrf
def Beacon(request):
  """Records result times in the datastore.
  This is the handler for after a test is done.
  ex: /beacon?category=reflow&csrf_token=number&results=tes1=150,test2=300
  """
  # First make sure this IP is not being an overachiever ;)
  ip = request.META.get('REMOTE_ADDR')
  ip_hash = hashlib.md5(ip).hexdigest()

  user_agent_string = request.META.get('HTTP_USER_AGENT')
  if not CheckThrottleIpAddress(ip_hash, user_agent_string):
    return http.HttpResponseServerError(BAD_BEACON_MSG + 'IP')

  js_user_agent_string = request.REQUEST.get('js_ua')

  callback = request.REQUEST.get('callback')
  category = request.REQUEST.get('category')
  results_str = request.REQUEST.get('results')
  params_str = request.REQUEST.get('params')

  if not category or not results_str:
    logging.debug('Got no category or results.')
    return http.HttpResponse(BAD_BEACON_MSG + 'Category/Results')
  if settings.BUILD == 'production' and category not in settings.CATEGORIES:
    # Allows local developers to try out category beaconing.
    logging.debug('Got a bogus category(%s) in production.' % category)
    return http.HttpResponse(BAD_BEACON_MSG + 'Category in Production')
  if not all_test_sets.HasTestSet(category):
    logging.debug('Could not get a test_set for category: %s' % category)
    return http.HttpResponse(BAD_BEACON_MSG + 'TestSet')

  test_set = all_test_sets.GetTestSet(category)

  logging.info('Beacon category: %s\nresults_str: %s' % (category, results_str))
  logging.info('js_user_agent_string: %s' % js_user_agent_string)

  if params_str:
    params_str = urllib.unquote(params_str)
  result_parent = ResultParent.AddResult(
      test_set, ip_hash, user_agent_string, results_str, params_str=params_str,
      js_user_agent_string=js_user_agent_string)
  if not result_parent:
    return http.HttpResponse(BAD_BEACON_MSG + 'ResultParent')
  ScheduleRecentTestsUpdate()

  if callback:
    return http.HttpResponse(BEACON_COMPLETE_CB_RESPONSE)
  else:
    # Return a successful, empty 204.
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


def GetStats(request, test_set, output='html',  opt_tests=None,
             use_memcache=True):
  """Returns the stats table.
  Args:
    request: a request object.
    test_set: a TestSet instance.
    output: Output type html or pickle or else you get a dict of params.
    opt_tests: list of tests.
    use_memcache: Use memcache or not.
  """
  category = test_set.category
  logging.info('GetStats for %s' % category)
  version_level = request.GET.get('v', 'top')
  is_skip_static = request.GET.get('sc')  # 'sc' for skip cache
  browser_param = request.GET.get('ua')
  results_str = request.GET.get('%s_results' % category, '')
  current_user_agent_string = request.META['HTTP_USER_AGENT']

  if (not is_skip_static and category in settings.STATIC_CATEGORIES
      and output in ('html', 'xhr')):
    # Use pickle'd data to which we can integrate a user's results.
    static_source = settings.STATIC_SOURCE_FORMAT % {
        'category': category,
        'version_level': version_level
        }
    if static_source.startswith('http'):
      response = urlfetch.fetch(static_source)
      stats_data = pickle.loads(response.content)
    else:
      stats_data = pickle.load(open(static_source))
    browsers = stats_data.keys()
    result_stats.CategoryBrowserManager.SortBrowsers(browsers)
    logging.info('Retrieved static stats: category=%s', category)
  else:
    if browser_param:
      browsers = browser_param.split(',')
    else:
      browsers = result_stats.CategoryBrowserManager.GetBrowsers(
          category, version_level)
    stats_data = result_stats.CategoryStatsManager.GetStats(
        test_set, browsers=browsers, use_memcache=use_memcache)

  # If the output is pickle, we are done and need to return a string.
  if output == 'pickle':
    return pickle.dumps(stats_data)

  results = None
  if results_str:
    results = test_set.ParseResults(results_str, ignore_key_errors=True)

  # Set current_browser to one in browsers or add it if not found.
  current_browser = UserAgent.factory(current_user_agent_string).pretty()
  for browser in browsers:
    if current_browser.startswith(browser):
      current_browser = browser
      break
  else:
    if results:
      UserAgentGroup.InsortBrowser(browsers, current_browser)

  # Adds the current results into the stats_data dict.
  if results:
    current_stats = test_set.GetStats(results)
    current_stats = test_set.GetStats(
        dict((k, (v, 1)) for k, v in results.items()))
    browser_stats = stats_data.setdefault(current_browser, {})
    browser_stats['current_results'] = current_stats['results']
    browser_stats['current_score'] = current_stats['summary_score']
    browser_stats['current_display'] = current_stats['summary_display']

  tests = opt_tests or test_set.tests
  visible_tests = [test for test in tests if test.IsVisible()]

  params = {
    'category': category,
    'category_name': test_set.category_name,
    'tests': visible_tests,
    'v': version_level,
    'user_agents': browsers,
    'request_path': request.get_full_path(),
    'current_user_agent': current_browser,
    'stats': stats_data,
    'params': test_set.default_params,
    'results_uri_string': results_str
  }
  #logging.info("GetStats got params: %s", str(params))
  if output in ['html', 'xhr']:
    return GetStatsDataTemplatized(params, 'table')
  elif output == 'csv':
    return GetStatsDataTemplatized(params, 'csv')
  else:
    return params


def GetStatsDataTemplatized(params, template='html'):
  """Returns the stats table run through a template.

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
  params['browser_nav'] = result_stats.BROWSER_NAV
  params['is_admin'] = users.is_current_user_admin()
  if not re.search('\?', params['request_path']):
    params['request_path'] = params['request_path'] + '?'
  t = loader.get_template('stats_%s.html' % template)
  html = t.render(Context(params))
  return html


@decorators.dev_appserver_only
@decorators.admin_required
def SeedDatastore(request):
  """Seed Datastore."""

  NUM_RECORDS = 1
  category = request.GET.get('category')
  if category:
    categories = [category]
  else:
    categories = settings.CATEGORIES
  increment_counts = request.GET.get('increment_counts', True)
  if increment_counts == '0':
    increment_counts = False

  def _GetRandomScore(test):
    return random.randrange(test.min_value, test.max_value + 1)

  for user_agent_string in TOP_USER_AGENT_STRINGS:
    user_agent = UserAgent.factory(user_agent_string)
    logging.info(' - user_agent: %s', user_agent.pretty())
  for category in categories:
    test_set = all_test_sets.GetTestSet(category)
    logging.info(' -- category: %s', category)
    for user_agent_string in TOP_USER_AGENT_STRINGS:
      logging.info(' ---- browser: %s',
                   UserAgent.factory(user_agent_string).pretty())
      for i in range(NUM_RECORDS):
        results_str = ','.join(['%s=%s' % (test.key, _GetRandomScore(test))
                               for test in test_set.tests])
        params_str = None
        if test_set.default_params:
          params_str = str(test_set.default_params)
        result_parent = ResultParent.AddResult(
            test_set, '1.2.3.4', user_agent_string, results_str, params_str)
        logging.info(' ------ AddResult, %s of %s: %s',
                     i + 1, NUM_RECORDS, results_str)
        if increment_counts:
          result_parent.increment_all_counts()
          logging.info(' ------ INCREMENTED ALL COUNTS')

  memcache.flush_all()
  return http.HttpResponseRedirect('?message=Datastore got seeded.')


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
  user_agent = query.get()
  if not user_agent:
    return http.HttpResponse('All Done!')

  # Do something with user_agent here.

  params = {
    'next_url': '/update_datastore?key=%s' % user_agent.key(),
    'current_name': user_agent.get_string_list(),
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
