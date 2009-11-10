#!/usr/bin/env python

# compares django's simplejson, simplejson, pickle and cPickle

import logging
import timeit


MODULES = []
import django.utils.simplejson
MODULES.append(('django', django.utils.simplejson, '33FF33'))
try:
  import simplejson
  MODULES.append(('simplejson', simplejson, '9900FF'))
except ImportError:
  pass

import pickle
MODULES.append(('pickle', pickle, 'FF0033'))

import cPickle
MODULES.append(('cpickle', cPickle, '3366FF'))

try:
  import json
  MODULES.append(('json', json, '00FF00'))
except ImportError:
  pass

import django
from django import http

# extra colors: '2211EE', '99AAFF'

NUM_RUNS = 10

module = None
serialized_data = None
def loads():
    module.loads(serialized_data)

data = None
def dumps():
    return module.dumps(data)


def GraphIt(request):
  dumps_results = []
  loads_results = []
  labels = []
  colors = []

  global data
  global serialized_data
  global module

  logging.info('load data')
  data = pickle.load(open('static_mode/network_3.py', 'r'))

  logging.info('start loop')
  for label, module, color in MODULES:
    logging.info('a')
    serialized_data = module.dumps(data)
    logging.info('b')
    loads_results.append(timeit.Timer(
        'loads()', 'from %s import loads' % __name__).timeit(number=NUM_RUNS))
    logging.info('c')
    dumps_results.append(timeit.Timer(
        'dumps()', 'from %s import dumps' % __name__).timeit(number=NUM_RUNS))
    logging.info('d')
    labels.append(label)
    colors.append(color)
  loads_chart_url = "http://chart.apis.google.com/chart?cht=bhs&chd=t:%s&chdl=%s&chco=%s&chs=450x200&chg=20&chxt=x&chx0=0,100" % (','.join(['%0.2f' % x for x in loads_results]), '|'.join(labels), '|'.join(colors))
  dumps_chart_url = "http://chart.apis.google.com/chart?cht=bhs&chd=t:%s&chdl=%s&chco=%s&chs=450x200&chg=20&chxt=x&chx0=0,100" % (','.join(['%0.2f' % x for x in dumps_results]), '|'.join(labels), '|'.join(colors))
  return http.HttpResponse("""<img src='%s'><br><img src='%s'>""" % (loads_chart_url, dumps_chart_url))
