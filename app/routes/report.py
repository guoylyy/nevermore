#!/usr/bin/python
# -*- coding: utf-8 -*-
from app import app, mongo, db, mongoClientDB
from flask import jsonify, request
from bson.objectid import ObjectId
from collections import OrderedDict

import json

class BaseResult:
  def __init__(self, code, data):
    self.code = code
    self.data = data
  def to_dict(self):
    return dict(
        code=self.code,
        data=self.data
      )

class Answer:
  def __init__(self, answer_type, answer, answer_range):
    self.answer_type = answer_type
    self.answer = answer
    self.answer_range = answer_range
  def to_dict(self):
    return dict(
        answer_type=self.answer_type,
        answer=self.answer,
        answer_range = self.answer_range
      )

# 保存实验报告
@app.route('/report/save', methods=['POST'])
def save_report():

  form = json.loads(request.data,object_pairs_hook=OrderedDict)

  student_id = form["student_id"]
  experiment_id = form["experiment_id"]
  report = form["report"]

  query_report = mongo.db.reports.find_one({"student_id":student_id,"experiment_id":experiment_id})

  if not query_report:
    mongo.db.reports.insert({"student_id":student_id,"experiment_id":experiment_id,"report":report,"status":"uncommitted"})
  else:
    mongo.db.reports.save({"_id":ObjectId(query_report["_id"]),"student_id":student_id,"experiment_id":experiment_id,"report":report,"status":"uncommitted"})
  
  return jsonify(BaseResult("200",report).to_dict())

# 获取实验报告
@app.route('/report/<int:student_id>/<int:experiment_id>', methods=['GET'])
def get_report(student_id,experiment_id):
  
  result = mongo.db.reports.find_one({"student_id":student_id,"experiment_id":experiment_id})

  if not result:
    return jsonify(BaseResult("404","Not Found").to_dict())
  return jsonify(BaseResult("200",{"report":result["report"],"status":result["status"]}).to_dict())

# 获取实验报告模板
@app.route('/report/template/<int:experiment_id>', methods=['GET'])
def get_answer(experiment_id):

  print experiment_id
  
  report = mongo.db.templates.find_one({"experiment_id":experiment_id})["template"]

  return jsonify(BaseResult("200",report).to_dict())

# 获取正确答案
@app.route('/report/answer/<int:experiment_id>', methods=['GET'])
def get_template(experiment_id):

  print experiment_id
  
  report = mongo.db.answers.find_one({"experiment_id":experiment_id})["report"]

  return jsonify(BaseResult("200",report).to_dict())

# 提交实验报告并打分
@app.route('/report/submit', methods=['POST'])
def submit_report():
  form = request.json

  student_id = form["student_id"]
  experiment_id = form["experiment_id"]
  
  #获得有序的report
  student_report_with_id = mongoClientDB['reports'].find_one({"student_id":student_id,"experiment_id":experiment_id})
  student_report = student_report_with_id["report"]
  answer_report = mongoClientDB['answers'].find_one({"experiment_id":experiment_id})["report"]

  graded_report = grade(student_report, answer_report)

  mongo.db.reports.save({"_id":ObjectId(student_report_with_id["_id"]),"student_id":student_id,"experiment_id":experiment_id,"report":graded_report,"status":"committed"})

  return jsonify(BaseResult("200",graded_report).to_dict())

# 根据answer_report批改student_report
def grade(student_report, answer_report):
  answers = []
  find_all_answers(answer_report, answers)
  answers.reverse()
  grade_all_answers(student_report, answers)
  return student_report

# 根据顺序的answers批改student_report
def grade_all_answers(node, answers):
  if isinstance(node, dict) :
    for x in range(len(node)):
      temp_key = node.keys()[x]
      temp_value = node[temp_key]
      #print temp_key
      if temp_key == 'answer':
        answer = answers.pop()
        #print answer.answer
        if answer.answer_type == 'fill-in-the-blank':
          lower_bound = answer.answer - answer.answer_range
          upper_bound = answer.answer + answer.answer_range
          #print lower_bound, upper_bound
          if lower_bound <= temp_value <= upper_bound:
            node["score"] = 1
          else:
            node["score"] = 0
        else:
          if temp_value == answer.answer:
            node["score"] = 1
          else:
            node["score"] = 0
      grade_all_answers(temp_value, answers)
  if isinstance(node, list) :
    for x in node:
      grade_all_answers(x, answers)

# 将answer_report中的所有answer按顺序存入answers
def find_all_answers(node, answers):
  if isinstance(node, dict) :
    for x in range(len(node)):
      temp_key = node.keys()[x]
      temp_value = node[temp_key]
      #print temp_key
      if temp_key == 'answer':
        answer = temp_value
        answer_type = node['type']
        if answer_type == 'fill-in-the-blank':
          answer_range = node['range']
          #print answer_type, answer, answer_range
          answers.append(Answer(answer_type, answer, answer_range))
        else:
          #print answer_type, answer
          answers.append(Answer(answer_type, answer, 0))
      find_all_answers(temp_value, answers)
  if isinstance(node, list) :
    for x in node:
      find_all_answers(x, answers)
