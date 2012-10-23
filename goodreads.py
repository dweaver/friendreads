from pprint import pprint
import os
import json
import urllib

import requests
CONFIG_DIR='.'

class GoodReads():
    baseurl = 'http://www.goodreads.com'

    def __init__(self, oauth_token=None):
        pprint(os.environ)
        self.key = os.environ['GOODREADS_KEY']
        self.secret = os.environ['GOODREADS_SECRET']
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
