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
import urllib2
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
            (r"/?", FriendsHandler),
            (r"/login", LoginHandler),
            (r"/callback", CallbackHandler),
        ]
        settings = dict(
            template_path =
                os.path.join(os.path.dirname(__file__), "templates"),
            static_path =
                os.path.join(os.path.dirname(__file__), "templates/static"),
            debug=True,
            cookie_secret = "YOUR_SECRET_HERE",
            )
        tornado.web.Application.__init__(self, 
                                        handlers, 
                                        **settings)


class FriendsHandler(tornado.web.RequestHandler):
    def get(self):
        gr = goodreads.GoodReads()
        token = self.get_secure_cookie('goodreads_token')
        if token:
            books = [{'name': 'The Great Gatsby', 
                'stars': 4.0,
                'num_reviews': 10}, 
                {'name': 'The Visual Display of Quantitative Information',
                    'stars': 4.3,
                    'num_reviews': 2},
                {'name': 'Women',
                    'stars': 3.9,
                    'num_reviews': 2}]
            self.render("home.html", books=books)
        else:
            self.write(
                    '<a href="{0}">Login on GoodReads</a>'.format(
                        gr.get_authurl('http://friendreads.herokuapp.com')))

        

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("login.html")

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
