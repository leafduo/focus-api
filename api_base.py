#!/usr/bin/env python2.6
# vim: set fileencoding=utf-8

import functools
import tornado.web
import base64
from bson.objectid import ObjectId
from password import Password

class BaseHandler(tornado.web.RequestHandler):
    """A base handler that provide lots of convient methods."""

    @property
    def mongo(self):
        return self.application.mongo

    @property
    def fs(self):
        return self.application.fs

    @property
    def user_role(self):
        return self.get_user_role();

    def get_current_user(self):
        """Set current user, authenticated via HTTP basic auth"""

        auth_header = self.request.headers.get('Authorization')
        if auth_header is None or not auth_header.startswith('Basic '):
            return None
        auth_decoded = base64.decodestring(auth_header[6:])
        if not auth_decoded.count(':'):
            return None
        login, password = auth_decoded.split(':', 2)
        if not login or not password: return None

        try:
            encrypted_password = self.mongo.user.find_one({'_id': login},
                    {'password': 1})['password']
        except:
            return None
        if encrypted_password and Password.verify(password, encrypted_password):
            return login
        else:
            return None

    def get_user_role(self):
        """Get the role of user, can be fellow or admin."""

        role = self.mongo.user.find_one({'_id': self.current_user},
                {'role': 1})['role']
        return role

    def str2bool(self, v):
        if isinstance(v, bool):
            return v
        return v.lower() in ('yes', 'true', '1', 't')

    _ARG_DEFAULT = []

    def get_bool_argument(self, name, default=_ARG_DEFAULT, strip=True):
        if default is not self._ARG_DEFAULT:
            arg = self.get_argument(name, default=default, strip=strip)
        else:
            arg = self.get_argument(name, strip=strip)
        return self.str2bool(arg)

    def _make_serializable(self, d):
        for key in d:
            if isinstance(d[key], ObjectId):
                d[key] = str(d[key])
            elif isinstance(d[key], dict):
                self._make_serializable(d[key])

    def finish(self, chunk=None):
        """Overwrite finish() for encoding API result to JSON"""
        if hasattr(self, 'res'):
            self._make_serializable(self.res)
            self.write(self.res)
        #call super class
        tornado.web.RequestHandler.finish(self, chunk)

    def restrict_to(self, d, it):
        """delete all items in dictionary except items whose keys in it (iterable)"""
        for k in d.keys():
            if k not in it:
                del d[k]
        return d


def auth(method):
    """Decoreator for APIs which need authorization"""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            raise tornado.web.HTTPError(401)
        return method(self, *args, **kwargs)
    return wrapper

def json(method):
    """Decoeate if we need to decode request body into json.

    The decoded json will be a dict named req.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            self.req = tornado.escape.json_decode(self.request.body)
        except:
            raise tornado.web.HTTPError(400)
        def ensure_not_none(d):
            for value in d.itervalues():
                if value is None:
                    raise tornado.web.HTTPError(400)
                elif isinstance(value, dict):
                    ensure_not_none(value)
        ensure_not_none(self.req)

        return method(self, *args, **kwargs)
    return wrapper
