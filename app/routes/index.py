#!/usr/bin/python
# -*- coding: utf-8 -*-
from app import app, mongo, db
from flask import abort, jsonify, request
from flask.ext.mongoengine.wtf import model_form
from bson.objectid import ObjectId
from bson import json_util


class Users(db.Document):
  _id = db.StringField(max_length=50)

  def to_dict(self):
    return dict(
        id=self._id
      )

# flask-mongoengine插入通过
@app.route('/me-test', methods=['POST'])
def me_test_insert():
  user = Users()
  user = user.save()
  print user._id
  return jsonify(user.to_dict())

# flask-mongoengine获取通过
@app.route('/me-test/<ObjectId:id>', methods=['GET'])
def me_test_find(id):
  user = Users.objects.get_or_404(_id=id)
  return json_util.dumps(user.to_dict())

# flask-pymongo 插入测试通过
@app.route('/pm-test', methods=['POST'])
def pm_test_insert():
  result = request.json
  mongo.db.users.insert({'aa':result})
  print result
  return jsonify(result)

# falsk-pymongo 获取测试通过
@app.route('/pm-test/<ObjectId:id>', methods=['GET'])
def pm_test(id):
  print id
  user = mongo.db.users.find_one_or_404(id)
  return json_util.dumps(user)



