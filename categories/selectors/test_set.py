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

"""Test Definitions."""

__author__ = 'elsigh@google.com (Lindsey Simon)'


from decimal import Decimal
import logging

from categories import test_set_base


_CATEGORY = 'selectors'


class SelectorsTest(test_set_base.TestBase):
  TESTS_URL_PATH = '/%s/test' % _CATEGORY

  def __init__(self, key, name, doc):
    """Initialze a benchmark test.

    Args:
      key: key for this in dict's
      name: a human readable label for display
      doc: a description of the test
    """
    test_set_base.TestBase.__init__(
        self,
        key=key,
        name=name,
        doc=doc,
        url=self.TESTS_URL_PATH,
        min_value=0,
        max_value=2200)


_TESTS = (
  # key, name, doc
  #SelectorsTest('score', 'Score', 'Selectors API test score'),
  SelectorsTest('passed', 'Passed', 'Selectors API tests passed'),
  SelectorsTest('failed', 'Failed', 'Selectors API tests failed')
)


class SelectorsTestSet(test_set_base.TestSet):

  def GetTestScoreAndDisplayValue(self, test_key, raw_scores):
    """Get a normalized score (1 to 10) and a value to output to the display.

    Args:
      test_key: a key for a test_set test.
      raw_scores: a dict of raw_scores indexed by test keys.
    Returns:
      score, display_value
          # score is from 1 to 10.
          # display_value is the text for the cell.
    """
    raw_score = raw_scores.get(test_key, 0)
    score = 0
    if test.key == 'passed':
      if raw_score >= 2100:
        score = 10
      elif raw_score >= 2000:
        score = 9
      elif raw_score >= 1950:
        score = 8
      elif raw_score >= 1800:
        score = 7
      else:
        score = 5
    elif test.key == 'failed':
      if raw_score == 0:
        score = 10
      elif raw_score <= 5:
        score = 9
      elif raw_score <= 20:
        score = 8
      else:
        score = 5
    return score, str(raw_score)

  def GetRowScoreAndDisplayValue(self, results):
    """Get the overall score for this row of results data.

    Args:
      results: {
          'test_key_1': {'score': score_1, 'raw_score': raw_score_1, ...},
          'test_key_2': {'score': score_2, 'raw_score': raw_score_2, ...},
          ...
          }
    Returns:
      score, display_value
          # score is from 1 to 10.
          # display_value is the text for the cell.
    """
    #logging.info('%s GetRowScore, results:%s' % (self.category, results))
    passed = results.get('passed', {}).get('raw_score', None)
    failed = results.get('failed', {}).get('raw_score', None)
    if passed is not None and failed is not None:
      percent_passed = 100.0 * passed / (passed + failed)
      if percent_passed:
        return self.Convert100Base10(percent_passed), '%.1f%%' % percent_passed
      else:
        return 1, '0%'
    else:
      return 0, ''


TEST_SET = SelectorsTestSet(
    category=_CATEGORY,
    category_name='Selectors API',
    tests=_TESTS
)
