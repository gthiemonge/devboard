import hashlib
import json
import logging
import os
import re
import stat
import time
import urllib

import requests


LOG = logging.getLogger(__name__)

urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.INFO)


class HttpException(Exception):
    pass


class APICache(object):
    def __init__(self, namespace):
        self.namespace = namespace
        self.cache = {}

        self.cache_dir = os.path.join(
                os.environ['HOME'], '.cache',
                namespace)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get(self, h, ttl, not_before):
        path = f'{self.cache_dir}/{h}.cache'
        if os.path.exists(path):
            s = os.stat(path)
            now = time.time()
            mtime = s[stat.ST_MTIME]
            if not_before:
                ref = time.mktime(not_before.timetuple())
                if mtime < ref:
                    return None
            if ttl == 0 or mtime + ttl >= now:
                with open(path) as fp:
                    # LOG.debug(f'Reading from {path}')
                    return json.load(fp)
        return None

    def set(self, h, data):
        path = f'{self.cache_dir}/{h}.cache'
        with open(path, 'w') as fp:
            # LOG.debug(f'Writing to {path}')
            fp.write(json.dumps(data))

    def digest(self, key):
        m = hashlib.sha256()
        m.update(key.encode('utf-8'))
        return m.hexdigest()

    def __call__(self, func):
        def wrapper(url, ttl=3600, not_before=None, force=False, **kwargs):
            key = "{}#{}".format(
                url,
                urllib.parse.urlencode(kwargs.get('params', {})))
            h = self.digest(key)

            if not force:
                c = self.get(h, ttl, not_before)
                if c is not None:
                    return c

            r = func(url, **kwargs)
            self.set(h, r)

            return r
        return wrapper


def handle_response(r):
    if r.status_code >= 400:
        raise HttpException("Response code {}: {}".format(
            r.status_code, r.text.split('\n', 1)[0]))
    if r.headers.get('Content-Type').startswith('application/json'):
        if r.text.startswith(')]}'):
            data = r.text.split('\n', 1)[1]
            return json.loads(data)
        return r.json()
    return r.text


def clean_url(url):
    url = re.sub('(token|key)=([^&]*)(&|$)', '\\1=XXX\\3', url)
    return url


@APICache('devboard')
def get(url, **kwargs):
    LOG.debug("GET {}".format(clean_url(url)))
    r = requests.get(url, **kwargs)
    LOG.debug("returned {}".format(r.status_code))
    return handle_response(r)


def post(url, **kwargs):
    LOG.debug("POST {}".format(clean_url(url)))
    r = requests.post(url, **kwargs)
    LOG.debug("returned {}".format(r.status_code))
    return handle_response(r)


def put(url, **kwargs):
    LOG.debug("PUT {}".format(clean_url(url)))
    r = requests.put(url, **kwargs)
    LOG.debug("returned {}".format(r.status_code))
    return handle_response(r)


def delete(url, **kwargs):
    LOG.debug("DELETE {}".format(clean_url(url)))
    r = requests.delete(url, **kwargs)
    LOG.debug("returned {}".format(r.status_code))
    return handle_response(r)
