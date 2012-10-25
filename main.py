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
            (r"/login", AuthHandler),
            (r"/list", ListHandler),
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

class AuthHandler(tornado.web.RequestHandler,
                     goodreads.GoodreadsMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("oauth_token", None):
            print ("Got oauth_token in callback")
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authorize_redirect(callback_uri="http://localhost:5001/login")

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Goodreads auth failed")

        print("user (in _on_auth)")
        pprint(user)

        self.set_secure_cookie("user", tornado.escape.json_encode(user))

        #self.set_secure_cookie("access_token", unicode(user['access_token']))
        #self.set_secure_cookie("id", unicode(user['id']))
        #self.write("access_token: {0}<br>".format(unicode(user['access_token'])))
        #self.write("id: {0}<br>".format(unicode(user['id'])))
        #self.write("What now?")
        #self.finish()
        #self.redirect('/')
        self.redirect('/list')
        

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        print("user_json: " + user_json)
        if user_json:
            return tornado.escape.json_decode(user_json)

class ListHandler(BaseHandler, 
                    goodreads.GoodreadsMixin):
    @tornado.web.asynchronous
    def get(self):
        self.write("About to add book to shelf!")
        self.write(tornado.escape.json_encode(self.current_user["access_token"]))
        self.goodreads_request(
            "/shelf/add_to_shelf.xml",
            post_args={'name': 'to-read', 'book_id': 6801825},
            access_token=self.current_user["access_token"],
            callback=self.async_callback(self._on_post))

    def _on_post(self, response):
        self.write('new_entry: ' + str(new_entry))
        self.finish("Done!") 


class MainHandler(BaseHandler,
                  goodreads.GoodreadsMixin):
    @tornado.web.asynchronous
    @tornado.web.authenticated
    def get(self):
        body = urllib.urlencode({'name': 'to-read', 'book_id': 6801825})
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        # TODO: headers?
        print("self.current_user['access_token']: " + tornado.escape.json_encode(self.current_user['access_token']))
        self.goodreads_request(
            "/shelf/add_to_shelf.xml",
            post_args={'name': 'to-read', 'book_id': 6801825},
            access_token=self.current_user["access_token"],
            callback=self.async_callback(self._on_post))

    def _on_post(self, response):
        if response is not None:
            with ExceptionStackContext(handle_exc):
                response.rethrow()
        if not response:
            # Call failed; perhaps missing permission?
            print("not new_entry in _on_post")
            self.authorize_redirect(callback_uri="http://localhost:5001/login")
            return
        self.finish("Added a book!")


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(os.environ.get("PORT", 5001))

    # start it up
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
