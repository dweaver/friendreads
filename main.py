#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tornado app for goodreads friends listing application 
# Designed to be posted to Heroku (?.herokuapp.com)

import os.path
import os
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata
import json
import urllib
from pprint import pprint

import requests

import goodreads


# import and define tornado-y things
from tornado.options import define, options
define("port", default=5000, help="run on the given port", type=int)

# application settings and handle mapping info
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/?", MainHandler),
            (r"/login", GoodreadsHandler),
            #(r"/?", FriendsHandler),
            #(r"/login", LoginHandler),
            #(r"/callback?oauth_token=(.*)", CallbackHandler),
        ]
        settings = dict(
            template_path =
                os.path.join(os.path.dirname(__file__), "templates"),
            static_path =
                os.path.join(os.path.dirname(__file__), "templates/static"),
            debug=True,
            cookie_secret = "YOUR_SECRET_HERE",
            goodreads_consumer_key = os.environ['GOODREADS_KEY'],
            goodreads_consumer_secret = os.environ['GOODREADS_SECRET'],
            login_url = "http://localhost:5001/login",
            )
        tornado.web.Application.__init__(self, 
                                        handlers, 
                                        **settings)

class GoodreadsHandler(tornado.web.RequestHandler,
                     goodreads.GoodreadsMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authorize_redirect(callback_uri="http://localhost:5001/login")

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Goodreads auth failed")
        # Save the user using, e.g., set_secure_cookie()
        self.set_secure_cookie("access_token", unicode(user['access_token']))
        print("id: " + user['id'])
        self.set_secure_cookie("id", unicode(user['id']))
        # TODO: print next parameter, and redirect there?
        self.finish()
        

class MainHandler(tornado.web.RequestHandler,
                  goodreads.GoodreadsMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self):
        body = urllib.urlencode({'name': 'to-read', 'book_id': 6801825})
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        # TODO: headers?
        print("GOT HERE!")
        print("User access token: " + user["access_token"])
        self.goodreads_request(
            "/shelf/add_to_shelf.xml",
            post_args={'name': 'to-read', 'book_id': 6801825},
            access_token=user["access_token"],
            callback=self.async_callback(self._on_post))

    def _on_post(self, new_entry):
        if not new_entry:
            # Call failed; perhaps missing permission?
            self.authorize_redirect()
            return
        self.finish("Added a book!")


class CallbackHandler(tornado.web.RequestHandler):
    def get(self, oauth_token):
        self.set_secure_cookie('goodreads_token', oauth_token)

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(os.environ.get("PORT", 5001))

    # start it up
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
