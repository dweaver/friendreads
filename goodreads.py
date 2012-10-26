

from pprint import pprint
import os
import json
import urllib
import logging
from xml.dom import minidom

import tornado.auth
from tornado import httpclient
from tornado import escape
from tornado.httputil import url_concat
from tornado.util import bytes_type, b
import requests
CONFIG_DIR='.'

class GoodreadsMixin(tornado.auth.OAuthMixin):
    """GoodReads OAuth authentication.

    To authenticate with Goodreads, register your application with
    Goodreads at http://goodreads.com/api/keys. Then copy your key and
    secret to the application settings 'goodreads_consumer_key' and
    'goodreads_consumer_secret'. Use this Mixin on the handler for the URL
    you registered as your application's Callback URL.

    When your application is set up, you can use this Mixin like this
    to authenticate the user with Goodreads and get access to their stream::

        class GoodreadsHandler(tornado.web.RequestHandler,
                             tornado.auth.GoodreadsMixin):
            @tornado.web.asynchronous
            def get(self):
                if self.get_argument("oauth_token", None):
                    self.get_authenticated_user(self.async_callback(self._on_auth))
                    return
                self.authorize_redirect()

            def _on_auth(self, user):
                if not user:
                    raise tornado.web.HTTPError(500, "Goodreads auth failed")
                # Save the user using, e.g., set_secure_cookie()

    TODO: is the following relevant to Goodreads?
    The user object returned by get_authenticated_user() includes the
    attributes 'username', 'name', and all of the custom Twitter user
    attributes describe at
    http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-users%C2%A0show
    in addition to 'access_token'. You should save the access token with
    the user; it is required to make requests on behalf of the user later
    with goodreads_request().
    """
    _OAUTH_REQUEST_TOKEN_URL = "http://www.goodreads.com/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "http://www.goodreads.com/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "http://www.goodreads.com/oauth/authorize"
    _OAUTH_AUTHENTICATE_URL = "http://www.goodreads.com/oauth/authenticate"

    _OAUTH_NO_CALLBACKS = False

    def authenticate_redirect(self, callback_uri=None):
        """Just like authorize_redirect(), but auto-redirects if authorized.
        This is generally the right interface to use if you are using
        oodreads for single-sign on.
        """
        http = httpclient.AsyncHTTPClient()
        http.fetch(self._oauth_request_token_url(callback_uri=callback_uri), self.async_callback(
            self._on_request_token, self._OAUTH_AUTHENTICATE_URL, None))

    def goodreads_request(self, path, callback, access_token=None,
                           post_args=None, **args):
        """Fetches the given API path"

        The path should not include the format (we automatically append
        ".json" and parse the JSON output).

        If the request is a POST, post_args should be provided. Query
        string arguments should be given as keyword arguments.

        All the Goodreads methods are documented at
        http://www.goodreads.com/api

        Many methods require an OAuth access token which you can obtain
        through authorize_redirect() and get_authenticated_user(). The
        user returned through that process includes an 'access_token'
        attribute that can be used to make authenticated requests via
        this method. Example usage::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.GoodreadsMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                def get(self):
                    self.goodreads_request(
                        # TODO: use goodreads example
                        "/statuses/update",
                        post_args={"status": "Testing Tornado Web Server"},
                        access_token=user["access_token"],
                        callback=self.async_callback(self._on_post))

                def _on_post(self, new_entry):
                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        """
        if path.startswith('http:') or path.startswith('https:'):
            # Raw urls are useful for e.g. search which doesn't follow the
            # usual pattern: http://search.twitter.com/search.json
            url = path
        else:
            url = "http://www.goodreads.com" + path 
        # Add the OAuth resource request signature if we have credentials
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            method = "POST" if post_args is not None else "GET"
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method)
            args.update(oauth)
        if args:
            url += "?" + urllib.urlencode(args)
        callback = self.async_callback(self._on_goodreads_request, callback)
        http = httpclient.AsyncHTTPClient()
        print ("URL: " + url)
        if post_args is not None:
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            http.fetch(url, method="POST", body=urllib.urlencode(post_args),
                       callback=callback, headers=headers)
        else:
            http.fetch(url, callback=callback)

    def _on_goodreads_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                            response.request.url)
            callback(None)
            return
        callback(response.body)

    def _oauth_consumer_token(self):
        self.require_setting("goodreads_consumer_key", "Goodreads OAuth")
        self.require_setting("goodreads_consumer_secret", "Goodreads OAuth")
        return dict(
            key=self.settings["goodreads_consumer_key"],
            secret=self.settings["goodreads_consumer_secret"])

    def _oauth_get_user(self, access_token, callback):
        print("access_token: {0} in _oauth_get_user".format(access_token))
        callback = self.async_callback(self._parse_user_response, callback)
        self.goodreads_request(
                "http://www.goodreads.com/api/auth_user",
            access_token=access_token, callback=callback)

    def _parse_user_response(self, callback, user):
        """Parse response for user information"""
        if user:
            """<?xml version="1.0" encoding="UTF-8"?>
                <GoodreadsResponse>
                  <Request>
                    <authentication>true</authentication>
                      <key><![CDATA[swXIcJrZ02EYOOtyty8cQ]]></key>
                    <method><![CDATA[api_auth_user]]></method>
                  </Request>
                  <user id="125642">
                  <name>Dan Weaver</name>
                  <link><![CDATA[http://www.goodreads.com/user/show/125642-dan-weaver?utm_medium=api]]></link>
                </user>
                </GoodreadsResponse>"""
            print("user: " + user)
            xd = minidom.parseString(user)
            def get_val(name):
                return xd.getElementsByTagName(name)[0].firstChild.wholeText
            def get_attr(name, attr):
                return xd.getElementsByTagName(name)[0].attributes[attr].value
            user = {}
            user['name'] = get_val('name')
            user['id'] = get_attr('user', 'id')

        callback(user)



class GoodReads():
    baseurl = 'http://www.goodreads.com'

    def __init__(self, oauth_token=None):
        pprint(os.environ)
        self.key = os.environ['GOODREADS_KEY']
        self.secret = os.environ['GOODREADS_SECRET']
        print self.key
        print self.secret
        self.oauth_token = oauth_token

    def get_authurl(self, callback_url):
        return '{0}/oauth/authorize?oauth_callback={1}&key={2}'.format(
                self.baseurl, 
                urllib.quote_plus(callback_url),
                self.key)

    def get_friends(self): 
        pass 

    def get_book(self, title):
        r = requests.get('http://www.goodreads.com/book')
