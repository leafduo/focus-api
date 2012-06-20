#!/usr/bin/env python2.6
# vim: set fileencoding=utf-8

import datetime
import time
import tornado
import pymongo
from bson.objectid import ObjectId

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
            
class ProfileHandler(api_base.BaseHandler):
    """Get/Delete/Update user profile
    """
    api_path = '/profile/(.*)' 
    profile_key_modifiable = ('first_name', 'last_name', 'password')
    profile_key_checkable = ('first_name', 'last_name', 'role')
    
    @api_base.auth
    @api_base.json        
    def get(self,  mail):
        """Get user profile"""
        
        profile = self.mongo.user.find_one({"_id" : mail})
        
        if (profile == None):
            raise tornado.web.HTTPError(404)
        
        for profile_key in profile.keys():
            if profile_key not in profile_key_checkable:
                del(profile[profile_key])        
        self.res = profile
        
    @api_base.auth
    @api_base.json        
    def delete(self, mail):
        """Delete user profile"""

        if self.get_user_role() != 'admin':
            raise tornado.web.HTTPError(403)

        profile = self.mongo.user.find_one({"_id" : mail})
        
        if (profile == None):
            raise tornado.web.HTTPError(404)
        
        self.mongo.user.remove({"_id" : mail})

    @api_base.auth
    @api_base.json
    def put(self, email):
        """Modify a user profiles."""

        if self.get_user_role() != 'admin' and \
        not (self.get_user_role() == 'fellow' and self.req['email'] == self.current_user):
            raise tornado.web.HTTPError(403)

        if self.mongo.user.find_one({'_id': self.req['email']}) is None:
            raise tornado.web.HTTPError(404)

        date = {}
        for key in ('password', 'first_name', 'last_name', 'gender'):
            if self.req.has_key(key):
                date[key] = str(self.req[key])
                if key == 'password':
                    from password import Password
                    date[key] = Password.encrypt(date[key])
        try:
            self.mongo.user.update({'_id': self.req['email']}, {'$set': date})
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

class CommentHandler(api_base.BaseHandler):
    """respond to an activity."""

    api_path = '/activity/(.*)/comment'

    @api_base.auth
    @api_base.json
    def post(self, activity_id):
        activity_id = ObjectId(activity_id)
        activity = self.mongo.activity.find_one({'_id': activity_id})
        if activity is None:
            raise tornado.web.HTTPError(404)
        comment = {}
        comment['description'] = self.req['description']
        comment['created_at'] = int(time.time())
        comment['owner'] = self.current_user
        if activity.has_key('comment'):
            activity['comment'].append(comment)
        else: 
            activity['comment'] = [comment]
        self.mongo.activity.update({'_id': activity_id}, 
                {"$set": {'comment': activity['comment']}} )
    
