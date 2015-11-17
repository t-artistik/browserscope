# Introduction #

The current user agent parsing library in Browserscope needs to become its own project with its own maintainers. Browserscope should dogfood this project.


# Features #

  * **Parsing the User Agent String**

> useragentstring.com does a pretty great job of UI for explaining and parsing the bits of the UA string. While I find it fascinating to try to eek out every bit of data in the string, I think we only care about the following:
    * OS
    * Hardware(CPU family) - i.e. if we can tell that something is a Droid of a Blackberry 9800 that is cool
    * Language Tag( ?)
    * Renderer (i.e. Webkit, Trident, Presto)
    * Renderer Version
    * Browser Build which will be split into
      * Browser Family (i.e. Firefox, IE, Chrome, etc..)
      * Project Name (optional, i.e. Namoroka, Shiretoko)
      * Major Version
      * Minor Version
      * Version Third Bit

  * Front End for the project
    * Something not unlike useragentstring.com
    * Additionally offers the following download files
      1. A json dictionary for **download** (w/ referer check to prevent abuse) consisting of ` 'allknownuseragentstrings': { all bits and values as a list } `
      1. An ordered list of regular expressions and substitutions as necessary (see browserscope/models/user\_agent.py for an example) for capturing these bits.
        * This assumes the implementation is best accomplished with an ordered list of regular expressions. If that's not the case, this may make less sense.
      1. Simple examples using the above regexes in python, Java, PHP, ruby, perl and C++ for embedding into your own application.


# Unit Tests #

This project should be thoroughly unit tested to prevent regressions. Obviously ;)

# Open Source / Distribution #

This project should live on code.google.com or github and the web frontend should maybe run on Google App Engine (meaning the app code itself would need to be in either Java or python). It should be able to operate under the free quotas but if not, we will ask Google for support in terms of donating additional App Engine resources.

An important part of this project is to gather feedback from the community about the correctness of the results and try to incorporate that feedback back into the parser. This can be done via comments on a per UA basis perhaps..

Additionally, as a distribution idea, what about using pubsubhubbub to distribute the code for the regular expression strings and possibly even the JS detection algorithm? That would be the most realtime way to get the latest regexes for parsing the ua string from the interwebs.