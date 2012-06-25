from lettuce import *
from nose.tools import assert_equals
import requests
import subprocess

@before.each_scenario
def before(step):
    world.base = 'http://localhost:9000'
    subprocess.call(['mongorestore', '--db', 'focus',
        '--drop', 'features/mongodb/'])

@step('I am logged in as (.+) with password (.+)')
def login(step, username, password):
    world.username = username
    world.password = password

@step('I follow activity (.+)')
def follow(step, activity_id):
    world.activity_id = activity_id

@step('system shows operation completed successfully')
def result(step):
    r = requests.put(world.base + '/user/' + world.username +
            '/follow/activity/' + world.activity_id,
            data='{"follow": true}',
            auth=(world.username, world.password))
    assert_equals(r.status_code, 200)
