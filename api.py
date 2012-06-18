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
