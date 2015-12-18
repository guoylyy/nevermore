import os
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG_TB_PANELS= ['flask.ext.mongoengine.panels.MongoDebugPanel']

MONGODB_SETTINGS = {
  'db': 'nm',
  'port':27017,
  'host': 'mongodb://localhost/nm-dev',
  'username':'webapp',
  'password':'abc123'
}

PYMONGO_DBNAME='nm-dev'
PYMONGO_HOST='localhost'
PYMONGO_PORT=27017
