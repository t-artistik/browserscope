# Browserscope Roadmap #

This page is done in OKR (Objective, Key Result) style, and is essentially an high-level view of where we're heading with Browserscope. There are of course many related and tangential issues which can be found in our Issue Tracker.


---


## Indeterminate ##

**Objective**: Divorce Browserscope from its UA Parsing code.

**KR**: Spin up a UA Parser project, and have Browserscope dogfood that library/tool. For more info, check out the [[UA Parser Design Doc](http://code.google.com/p/browserscope/wiki/UserAgentParsing)]


## Q4 2010 ##

**Objective**: RichText2 as new test category

**KR**: Store the data - RichText2 includes a LOT of tests, so we'll have to do something to deal with parallelizing the storage process of records in order to collect data effectively.

**Objective**: UserTests browsing/sharing UI

**KR**: Start working on a UI for browsing existing tests to help developers bring attention to their work.

**KR**: Work with developer relations folks on some relevant visualizations for tests they've written.



---


## Q2 2010 ##

### The Scaling More Broadly Quarter (aka Fanout Filly) ###

[Q2-2010 Issues in our Issue Tracker](http://code.google.com/p/browserscope/issues/list?can=2&q=milestone=Q2-2010&colspec=ID%20Type%20Status%20Priority%20Milestone%20Owner%20Summary)

**Objective**: Allow users to run their own tests on Browserscope, visualize their results via the table and graphs, and download the result data.

**KR**: A user should be able write a config file defining their test, and then we'll host that test and store beacon'd results data for them. This will likely be a lot of work to do correctly and could reach into Q3.



---


## Q1 2010 ##

### The Begin Scaling More Broadly Quarter ###

[Q1-2010 Issues in our Issue Tracker](http://code.google.com/p/browserscope/issues/list?can=2&q=milestone=Q1-2010&colspec=ID%20Type%20Status%20Priority%20Milestone%20Owner%20Summary)

**Objective**: Be able to store more granular data for test results while compacting into < 15 table result columns.

**KR**: Bundled tests which actually represent a bunch of tests under the hood. Right now we're solving this problem in a non-scalable way with the GetRowScore method, but that requires all of the possible data for a row, and it's so slow that we have to fall back to static results tables (i.e. RichText). Our Selectors API results are missing all of the granularity from the 2000 tests currently due to this issue.


**Objective**: Work on a Design Doc for User-Uploaded tests

**KR**: A design doc that describes the upload format, scaling constraints, etc...

---

## Q4 2009 ##

### The Prepare to Scale More Broadly Quarter ###

[Q4-2009 Issues in our Issue Tracker](http://code.google.com/p/browserscope/issues/list?can=2&q=milestone=Q4-2009&colspec=ID%20Type%20Status%20Priority%20Milestone%20Owner%20Summary)

**Objective**: Be able to roll out median trees much more quickly.

**KR**: Overall, we need to be able to regenerate our median data more quickly to enable fixes to either the logic in calculating the results themselves or else when we fix User Agent classifications. This entails trying a variety of mechanisms to achieve this goal, i.e. offline SQL based updates, dynamic sampling, etc...


**Objective**: Expose Trending Graphs to evaluate browser progress.

**KR**: Right now our results tables take alot of inference in order to discern the speed of improvement over time and over versions. We should expose a gviz data provider backend that enables chart configurations as an alternate to the table view UI.


**Objective**: Add some interesting new test categories.

**KR**: 1-3 new test categories would be great.