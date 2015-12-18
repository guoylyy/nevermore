#!/usr/bin/python
# -*- coding: utf-8 -*-
from flask import Flask
from flask.ext.pymongo import PyMongo
from flask.ext.mongoengine import MongoEngine

app = Flask(__name__, static_url_path='')

#读取配置文件
app.config.from_object('config-dev') 

#配置flask-mongoengine
db = MongoEngine()
db.init_app(app)

#配置纯净的mongo连接器
mongo = PyMongo(app, config_prefix='PYMONGO')

#其他路由配置
from app.routes import index

