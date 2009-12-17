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
#from models.result import ResultParent
#from models.result import ResultTime
#from models.user_agent import UserAgent
#from models.user_agent import UserAgentGroup

from base import admin_rankers

# UpdateRankers
# - receive data to set LastNRanker or CountRanker

# Update Browser Counts
# - SetBrowsers - category, version_level, browsers
