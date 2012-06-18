from tornado.options import define, options

define("debug_mode", default=True, help="Debug mode enabled.")
define("port", default=9000, help="Port to listen.")
