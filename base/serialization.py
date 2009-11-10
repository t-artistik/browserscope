#!/usr/bin/env python

# compares django's simplejson, simplejson, pickle and cPickle

import timeit
import django.utils.simplejson
import pickle
import cPickle
import json

times = 100
print "Times are for %i iterations" % times

def bench(cmd, imprt):
    t = timeit.Timer(cmd, imprt)
    s = t.timeit(number=times)
    print "%s total=%02f avg=%02f" % (cmd, s, (s/times))
    return s

def django_loads():
    import django.utils.simplejson
    django.utils.simplejson.loads(file('words.json').read())

# def simplejson_loads():
#     simplejson.loads(file('words.json').read())

def pickle_loads():
    pickle.loads(file('words.pickle').read())

def cpickle_loads():
    cPickle.loads(file('words.pickle').read())

def cpickle1_loads():
    cPickle.loads(file('words.pickle1').read())

def cpickle2_loads():
    cPickle.loads(file('words.pickle2').read())

def json_loads():
    json.loads(file('words.json').read())

def GraphIt(request):
  b1 = bench('django_loads()', 'from __main__ import django_loads')
  # b2 = bench('simplejson_loads()', 'from __main__ import simplejson_loads')
  b3 = bench('pickle_loads()', 'from __main__ import pickle_loads')
  b4 = bench('cpickle_loads()', 'from __main__ import cpickle_loads')
  b5 = bench('cpickle1_loads()', 'from __main__ import cpickle1_loads')
  b6 = bench('cpickle2_loads()', 'from __main__ import cpickle2_loads')
  b7 = bench('json_loads()', 'from __main__ import json_loads')

  #print "http://chart.apis.google.com/chart?cht=bhs&chd=t:%0.2f,%0.2f,%0.2f,%0.2f,%0.2f,%0.2f,%0.2f&chdl=django|simplejson|pickle|cpickle|cpickle1|cpickle2|json&chco=33FF33|9900FF|FF0033|3366FF|2211EE|99AAFF|00FF00&chs=450x200&chg=20&chxt=x&chx0=0,100" % (b1, b2, b3, b4, b5, b6, b7)
  print "http://chart.apis.google.com/chart?cht=bhs&chd=t:%0.2f,%0.2f,%0.2f,%0.2f,%0.2f,%0.2f&chdl=django|pickle|cpickle|cpickle1|cpickle2|json&chco=33FF33|FF0033|3366FF|2211EE|99AAFF|00FF00&chs=450x200&chg=20&chxt=x&chx0=0,100" % (b1, b3, b4, b5, b6, b7)
