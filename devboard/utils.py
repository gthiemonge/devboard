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


class NetworkException(Exception):
    pass


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


def _handle_response(r):
    if r.status_code >= 400:
        raise HttpException("Response code {}: {}".format(
            r.status_code, r.text.split('\n', 1)[0:10]))
    if r.headers.get('Content-Type').startswith('application/json'):
        if r.text.startswith(')]}'):
            data = r.text.split('\n', 1)[1]
            return json.loads(data)
        return r.json()
    return r.text


def _clean_url(url):
    url = re.sub('(token|key)=([^&]*)(&|$)', '\\1=<edited>\\3', url)
    return url


def _request(method, url, **kwargs):
    LOG.debug("{} {}".format(method,
                             _clean_url(url)))

    func = getattr(requests, method.lower())
    try:
        r = func(url, **kwargs)
    except requests.exceptions.ConnectionError as e:
        LOG.error("Error while requesting {} {}: {}".format(
            method, _clean_url(url), e))
        raise NetworkException("Cannot connect to remote server")

    LOG.debug("returns {}".format(r.status_code))

    return _handle_response(r)


@APICache('devboard')
def get(url, **kwargs):
    return _request('GET', url, **kwargs)


def post(url, **kwargs):
    return _request('POST', url, **kwargs)


def put(url, **kwargs):
    return _request('PUT', url, **kwargs)


def delete(url, **kwargs):
    return _request('DELETE', url, **kwargs)
