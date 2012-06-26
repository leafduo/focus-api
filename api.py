#!/usr/bin/env python2.6
# vim: set fileencoding=utf-8

import datetime
import time
import tornado
import pymongo
from bson.objectid import ObjectId
import smtplib
from random import choice
import string
from password import Password

import api_base

class RootHandler(api_base.BaseHandler):
    """Root API that validates credentials.
    """

    api_path = '/'

    @api_base.auth
    def get(self):
        """Example API for authorization."""

class UserHandler(api_base.BaseHandler):
    """User handler, which can create user and modify user profiles.
    """

    api_path = '/user/([^/]*)'
    profile_key_modifiable = ('first_name', 'last_name', 'password',
            'status', 'gender', 'language', 'work_field', 'location',
            'population_target', 'mobile_countrycode', 'mobile',
            'email_type', 'street', 'city', 'province', 'zip', 'country',
            'skype_ID', 'organization_address', 'organization_name',
            'organization_acronym', 'organization_formed_date',
            'organization_website', 'organization_type',
            'organization_employee_num', 'organization_budget',
            'organization_phone_countrycode', 'organization_phone')
    profile_key_checkable = ('first_name', 'last_name', 'status', 'role',
            'gender', 'language', 'work_field', 'location',
            'population_target', 'mobile_countrycode', 'mobile',
            'email_type', 'street', 'city', 'province', 'zip',
            'country', 'skype_ID', 'organization_address',
            'organization_name', 'organization_acronym',
            'organization_formed_date', 'organization_website',
            'organization_type', 'organization_employee_num',
            'organization_budget', 'organization_phone_countrycode',
            'organization_phone')
    profile_key_enum = {'gender':('male', 'female', 'secrecy'),
            'role':('admin', 'fellow'), 'email_type':('home', 'business'),
            'organization_type':
            ('Private sector','Government Agency','Multilateral'),
            'organization_employee_num':
            ('less than 10', '11-25', '26-40', '41-60', '61-80', '81-100',
                '101-150', '151-200', 'more than 200'),
            'organization_budget':('less than $50,000', '$50,000-$100000',
                '$100,000-$200,000','$200,000-$500,000',
              '$500,000-$1,000,000', '$1,000,000-$5,000,000',
              '$5,000,000-$10,000,000', 'more than $10,000,000')}

    @api_base.auth
    @api_base.json
    def post(self, login):
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
                "role": self.req['role'],  'following': [], 'follower': [],
                'tags_following': [], 'activity_following': []})

        except pymongo.errors.DuplicateKeyError:
            raise tornado.web.HTTPError(422)

        useractivity = {"title": self.req['first_name'] + " Register", "type": "people",
                                   "description": "Hi,everyone. I'm " + self.req['first_name'] + ". Glad to join the OmarHub!",
                                   "owner": self.req['email'], "created_at": int(time.time()),
                                   "publish": True, "tags": ["User"]}
        self.mongo.activity.insert(useractivity)

        # send activation email
        cookbook = string.ascii_letters + string.digits
        link = ''.join([choice(cookbook) for i in range(0,64)])
        msg = 'This is from focus team, here is your activation link: \r\n' + link
        try:
            sendmail(self.req['email'], msg)
        except smtplib.SMTPHeloError:
            raise tornado.web.HTTPError(503)

        self.mongo.user.update({"_id": self.req['email']},
                {"$set": {"validation_link": link}})

    @api_base.auth
    def get(self, email):
        """Get user profile"""

        profile = self.mongo.user.find_one({"_id" : email})

        if (profile is None):
            raise tornado.web.HTTPError(404)

        self.res = self.restrict_to(profile, self.profile_key_checkable)

    @api_base.auth
    def delete(self, email):
        """Delete user profile"""

        if self.get_user_role() != 'admin':
            raise tornado.web.HTTPError(403)

        profile = self.mongo.user.find_one({"_id" : email})

        if (profile is None):
            raise tornado.web.HTTPError(404)

        self.mongo.user.remove({"_id" : email})

    @api_base.auth
    @api_base.json
    def put(self, email):
        """Modify user profile.
        """

        if self.get_user_role() != 'admin' and \
                not (self.get_user_role() == 'fellow' and \
                email == self.current_user):
                    raise tornado.web.HTTPError(403)

        if self.mongo.user.find_one({'_id': email}) is None:
            raise tornado.web.HTTPError(404)

        self.restrict_to(self.req, self.profile_key_modifiable)
        for key in self.req.keys():
            if key in self.profile_key_enum.keys():
                if self.req[key] not in self.profile_key_enum[key]:
                    raise tornado.web.HTTPError(400)

        if self.req.has_key('password'):
            from password import Password
            self.req['password'] = Password.encrypt(self.req['password'])

        try:
            self.mongo.user.update({'_id': email}, {'$set': self.req})
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

        activity_id = self.mongo.activity.insert(self.req)
        self.set_status(201)
        self.set_header('Location', '/activity/' + str(activity_id))

    @api_base.auth
    def get(self):
        offset = self.get_argument('offset', 0)
        limit = self.get_argument('limit', 20)
        activity_type = self.get_argument('type', None)
        sort_by = self.get_argument('sort_by', None)
        event_type = self.get_argument('event_type', None)
        followed = self.get_argument('followed', False)

        offset = int(offset)
        limit = int(limit)
        followed = bool(followed)
        if activity_type not in (None, 'offer', 'need', 'event', 'people'):
            raise tornado.web.HTTPError(400)
        if sort_by not in (None, 'most_followed', 'most_recent'):
            raise tornado.web.HTTPError(400)
        if activity_type != 'event' and event_type is not None:
            raise tornado.web.HTTPError(400)
        if event_type not in (None, 'upcoming', 'past', 'ongoing'):
            raise tornado.web.HTTPError(400)

        query = {}
        if activity_type:
            query['type'] = activity_type
        if event_type:
            now = int(time.time())
            if event_type == 'upcoming':
                query['start_at'] = {'$gt': now}
            elif event_type == 'ongoing':
                query['start_at'] = {'$lte': now}
                query['end_at'] = {'$gte': now}
            elif event_type == 'past':
                query['end_at'] = {'$lt': now}
        if followed:
            query['follower'] = {'$in': [self.current_user]}

        if sort_by == 'most_followed':
            sort = [('follower_count', pymongo.DESCENDING), ('created_at', pymongo.DESCENDING)]
        else:
            sort = [('created_at', pymongo.DESCENDING)]

        activity_array = self.mongo.activity.find(query).sort(sort).skip(offset).limit(limit)

        self.res = {'activity': []}
        for activity in activity_array:
            activity['id'] = str(activity['_id'])
            del(activity['_id'])
            del(activity['follower_count'])
            self.res['activity'].append(activity)

class EditActivityHandler(api_base.BaseHandler):
    """edit and delete an activity"""

    api_path = '/activity/([^/]*)'
    activity_key_modifiable = ('description', 'title', 'start_at', 'end_at',
    'publish')

    @api_base.auth
    def delete(self, activity_id):
        """delete activity"""

        activity_id = ObjectId(activity_id)
        activity = self.mongo.activity.find_one({"_id": activity_id})
        if (activity is None or activity["owner"] != self.current_user):
            raise tornado.web.HTTPError(404)
        self.mongo.user.remove({"_id": activity_id})

    @api_base.auth
    @api_base.json
    def put(self, activity_id):
        """Modify activity."""

        activity_id = ObjectId(activity_id)
        activity = self.mongo.activity.find_one({"_id": activity_id})
        if (activity is None or activity["owner"] != self.current_user):
            raise tornado.web.HTTPError(404)

        self.restrict_to(self.req, self.activity_key_modifiable)
        for key in self.req.keys():
            pass

class GetFollowHandler(api_base.BaseHandler):
    """Get follow status."""

    api_path = '/user/([^/]*)/follow'

    @api_base.auth
    def get(self, login):
        self.res = self.mongo.user.find_one({'_id': login}, {'following': 1, 'follower': 1,
            'tags_following': 1, 'activity_following': 1})
        self.res['email'] = str(login)
        del self.res['_id']

class PutFollowHandler(api_base.BaseHandler):
    """Modify follow status"""

    api_path = '/user/([^/]*)/follow/([^/]*)/([^/]*)'

    @api_base.auth
    @api_base.json
    def put(self, login, follow_type, follow_id):
        if self.current_user != login:
            raise tornado.web.HTTPError(403)
        if follow_type not in ('user', 'activity', 'tag'):
            raise tornado.web.HTTPError(400)
        follow_key = {'user': 'following', 'activity': 'activity_following',
                'tag': 'tags_following'}[follow_type]
        if follow_type != 'user':
            follow_id = ObjectId(follow_id)

        if self.req['follow']:
            if self.mongo.user.find_one({'_id': login,
                follow_key: follow_id}):
                raise tornado.web.HTTPError(409)
            self.mongo.user.update({'_id': login},
                    {'$push': {follow_key: follow_id}})
            self.mongo[follow_type].update({'_id': follow_id},
                    {'$push': {'follower': login},
                        '$inc': {'follower_count': 1}})
        else:
            self.mongo.user.update({'_id': login},
                    {'$pull': {follow_key: follow_id}})
            self.mongo[follow_type].update({'_id': follow_id},
                    {'$pull': {'follower': login},
                        '$inc': {'follower_count': -1}})

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

class ActivationHandler(api_base.BaseHandler):
    """activate the user"""

    api_path = '/user/validation/(\w+)'

    @api_base.json
    def put(self, validation_link):
        password = Password.encrypt(self.req['password'])
        self.mongo.user.update({"validation_link": validation_link},
                {"$set": {"password": password}})
        self.mongo.user.update({"validation_link": validation_link},
                {"$unset": {"validation_link": 1}})


def sendmail(toaddr, msg):
    """utility to send mail"""

    server = 'smtp.qq.com'
    fromaddr = '324823396@qq.com'
    s = smtplib.SMTP(server)
    s.set_debuglevel(1)
    s.login("324823396@qq.com","5gmailqq")
    s.sendmail(fromaddr,toaddr,msg)
    s.quit()
