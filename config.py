import os
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG_TB_PANELS= ['flask.ext.mongoengine.panels.MongoDebugPanel']

MONGODB_SETTINGS = {
  'db': 'nm',
  'host': 'mongodb://localhost/nm',
  'username':'webapp',
  'password':'abc123'
}