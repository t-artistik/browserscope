# Contributing to Browserscope #

We'd love for you to contribute to Browserscope. Our process is simple, just email a diff to the mailing list at browserscope@googlegroups.com explaining your patch, and we'll apply and submit it. Once we've committed a few of your patches, we'll make you a repository committer.

Follow the instructions below for getting started. If possible, try running the unit tests first by hitting /test in your dev environment (make sure you click the Sign in as Administrator checkbox in the local Sign In dialog).

## Setting up the dev environment ##

Browserscope is built on Google App Engine using the Django web application framework and written in Python.

  * Checkout a copy of the Browserscope source code using subversion, instructions at http://code.google.com/p/browserscope/source/checkout
  * Download the Google App Engine SDK from http://code.google.com/appengine/downloads.html
  * Install Django 1.1 on your machine - http://www.djangoproject.com/download/1.1.2/tarball/
  * Startup the server: ./pathto/google\_appengine/dev\_appserver.py --port=8080 browserscope

You should then be able to access the local application at: http://localhost:8080/

You can run the unit tests at: http://localhost:8080/test


## References ##
  * Browserscope Issue Tracker - http://code.google.com/p/browserscope/issues/list
  * App Engine Docs - http://code.google.com/appengine/docs/python/overview.html
  * App Engine Group - http://groups.google.com/group/google-appengine
  * Python Docs - http://www.python.org/doc/
  * Django - http://www.djangoproject.com/


## Adding a new test category ##

At the moment, the easiest thing is to write up a "user test" and then submit that to the mailing list for consideration. Definitely email the group too and look over our issue tracker to see if anyone is working on your idea already. We can do the work of integrating your test into the main suite and host it on browserscope.org.

Once all that's taken care of, to create a completely new test category:
  * Copy one of the existing directories in categories/
  * Edit your test\_set.py, handlers.py
  * Add your files in templates/ and static/
  * Update urls.py and settings.CATEGORIES
  * Follow the examples of other tests re:
    * beaconing using/testdriver\_base
    * your GetScoreAndDisplayValue method
    * your GetRowScoreAndDisplayValue method