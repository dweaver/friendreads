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
from tornado import httpclient
from tornado.stack_context import ExceptionStackContext
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
            (r"/add", AddHandler),
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

        self.set_secure_cookie("user", tornado.escape.json_encode(user))
        self.redirect('/')
        

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        print("user_json: " + user_json)
        if user_json:
            return tornado.escape.json_decode(user_json)

class AddHandler(BaseHandler, 
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
        self.write('response: ' + str(response))
        self.finish("Done!") 

from lxml.cssselect import CSSSelector 
from lxml import etree 

def todict(et, tag_list):
    '''helper function for converting one element deep etree into a 
       dictionary'''
    fn = lambda tag: et.find(tag).text
    d = {}
    for tag in tag_list:
        if type(tag) == str:
            d.setdefault(tag, fn(tag))
        else:
            d.setdefault(tag[0], tag[1](fn(tag[0])))

    return d 


class GoodParse():
    def parse(self, response):
        '''Parses <GoodreadsResponse> and returns Python data structure, 
            or False on failure'''
        print ("Parsing response of length {0}.".format(len(response)))
        et = etree.fromstring(response)
       
        get_method = CSSSelector('GoodreadsResponse > Request > method')
        method = get_method(et)[0].text
         
        METHODS = {"friend_user": self.friend_user,
                   "review_list": self.review_list}
        if method in METHODS:
            return METHODS[method](et) 
        else:
            return False

    def friend_user(self, et, init_friends=[]):
        friends = init_friends 
        get_users = CSSSelector('GoodreadsResponse > friends > user')
        for et_user in get_users(et):
            friends.append(todict(et_user, ['id', 'name', 'link']))
        return friends

    def review_list(self, et, init_reviews=[]):
        reviews = init_reviews
        get_reviews = CSSSelector('GoodreadsResponse > reviews > review')
        get_books = CSSSelector('book')
        for et_review in get_reviews(et):
            review = todict(et_review, [('rating', int)])
            if review['rating'] > 0:
                et_book = get_books(et_review)[0]
                book = todict(et_book, [('id', int), 
                    ('average_rating', float)])
                review.update(book)
                reviews.append(review)
        return reviews 


class ListHandler(BaseHandler, 
                    goodreads.GoodreadsMixin):
    @tornado.web.asynchronous
    def get(self):
        # get user's friends
        self.goodreads_request(
            "/friend/user.xml",
            post_args=dict(id = self.current_user['id'], 
                        sort = 'last_online'),
            access_token=self.current_user["access_token"],
            callback=self.async_callback(self._on_friends_response))

    def _on_friends_response(self, response):
        #self.write('response: ' + str(response))
        friends = GoodParse().parse(response)
        self.goodreads_request(
            "/review/list",
            post_args=dict(id=3322000, format='xml', v=2, shelf="read",
                per_page=200),
            access_token=self.current_user["access_token"],
            callback=self.async_callback(self._on_books_response))

    def _on_books_response(self, response):
        #self.write(response)
        books = GoodParse().parse(response)
        pprint(books) 
        self.finish("Done!")

class MainHandler(BaseHandler,
                  goodreads.GoodreadsMixin):
    @tornado.web.asynchronous
    @tornado.web.authenticated
    def get(self):
        self.goodreads_request(
            "/shelf/add_to_shelf.xml",
            post_args={'name': 'to-read', 'book_id': 153747},
            access_token=self.current_user["access_token"],
            callback=self.async_callback(self._on_post))

    def _on_post(self, response):
        def handle_exc(*args):
            print('Exception occured')
            return True

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
