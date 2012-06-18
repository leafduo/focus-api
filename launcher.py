#!/usr/bin/env python2.6
# vim: set fileencoding=utf-8

#Load local config
try:
    import config
except ImportError:
    print "no config was found."
    import sys
    sys.exit()

#System libraries
import sys
import base64
import os
import time
import inspect
import functools
import httplib

#Tornado related
import tornado.web
import tornado.options
import tornado.httpserver
from tornado.options import options

if options.debug_mode:
    import tornado.autoreload

import api #api list

class Application(tornado.web.Application):
    def __init__(self, **kargs):

        httplib.responses[422] = 'Unprocessable Entity'      #I like this status code, so I add it.

        handlers = [(obj.api_path, obj) for name, obj in inspect.getmembers(api) if inspect.isclass(obj) and hasattr(obj, "api_path")]

        print handlers

        # Have one global connection to the DB across all handlers
        import pymongo
        connection = pymongo.Connection(safe=True)
        self.mongo = connection.focus

        #import gridfs
        import gridfs
        self.fs = gridfs.GridFS(self.mongo)

        tornado.web.Application.__init__(self, handlers, **kargs)

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True)
    http_server.listen(options.port, address="127.0.0.1")

    #Enable autoreload in debug mode
    try:
        tornado.autoreload.start()
    except:
        pass

    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
