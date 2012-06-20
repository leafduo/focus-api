#!/usr/bin/env python2.6
# vim: set fileencoding=utf-8

import datetime
import time
import tornado
import pymongo

import api_base

class RootHandler(api_base.BaseHandler):
    """Root API that validates credentials.
    """

    api_path = '/'

    @api_base.auth
    def get(self):
        """Print a simple welcome message"""

class UserHandler(api_base.BaseHandler):
    """User handler, which can create user and modify user profiles.
    """

    api_path = '/user'

    @api_base.auth
    @api_base.json
    def post(self):
        """Create a new user."""

        if self.get_user_role() != 'admin':
            raise tornado.web.HTTPError(403)

        try:
            for key in ('email', 'first_name', 'last_name', 'role'):
                self.req[key] = str(self.req[key])
        except KeyError:
            raise tornado.web.HTTPError(400)

        if self.req['role'] not in ('fellow', 'admin'):
            raise tornado.web.HTTPError(400)

        self.req['created_at'] = int(time.time())

        try:
            self.mongo.user.insert({"_id": self.req['email'], "first_name":
                self.req['first_name'], "last_name": self.req['last_name'],
                "role": self.req['role']})
        except pymongo.errors.DuplicateKeyError:
            raise tornado.web.HTTPError(422)

class ActivityHandler(api_base.BaseHandler):
    """Post and view activities."""

    api_path = '/activity'

    @api_base.auth
    @api_base.json
    def post(self):
        try:
            for key in ('title', 'description', 'type'):
                self.req[key] = str(self.req[key])

            self.req['publish'] = bool(self.req['publish'])

            for key in ('start_at', 'end_at'):
                self.req[key] = int(self.req[key])
        except KeyError:
            raise tornado.web.HTTPError(400)

        self.req['owner'] = self.current_user
        self.req['created_at'] = int(time.time())

        if self.req['type'] not in ('offer', 'need', 'event'):
            raise tornado.web.HTTPError(400)
        if not isinstance(self.req['tags'], list):
            raise tornado.web.HTTPError(400)

        self.mongo.activity.insert(self.req)

    @api_base.auth
    def get(self):
        offset = self.get_argument('offset', 0)
        limit = self.get_argument('limit', 20)
        activity_array = self.mongo.activity.find(). \
                sort([('created_at', pymongo.DESCENDING)]).skip(offset).limit(limit)
        self.res = {'activity': []}
        for activity in activity_array:
            del(activity['_id'])
            self.res['activity'].append(activity)
