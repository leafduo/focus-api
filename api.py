#!/usr/bin/env python2.6
# vim: set fileencoding=utf-8

import tornado

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

        if self.get_user_role != 'admin':
            raise tornado.web.HTTPError(403)

        try:
            email = self.req['email']
            first_name = self.req['first_name']
            last_name = self.req['last_name']
            role = self.req['role']
        except KeyError:
            raise tornado.web.HTTPError(400)

        if role not in ('fellow', 'admin'):
            raise tornado.web.HTTPError(400)

        self.mongo.user.insert({"_id": email, "first_name": first_name,
            "last_name": last_name, "role": role})
