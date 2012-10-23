from os import path
import json
import urllib

import requests
CONFIG_DIR='../config/'

class GoodReads():
    baseurl = 'http://www.goodreads.com'

    def __init__(self, oauth_token=None):
        with open(path.join(CONFIG_DIR, 'goodreads.json')) as f:
            self.oauth_token = oauth_token
            # self.config is a dict containing goodreads account 
            # 'key' and 'secret'
            self.config = json.loads(f.read())

    def get_key(self):
        return self.config['key']

    def get_secret(self):
        return self.config['secret']

    def get_authurl(self, callback_url):
        return '{0}/oauth/authorize?key={1}'.format(
                self.baseurl, 
                urllib.quote_plus(callback_url),
                self.get_key())

    def get_friends(self): 
        pass 

    def get_book(self, title):
        r = requests.get('http://www.goodreads.com/book')
