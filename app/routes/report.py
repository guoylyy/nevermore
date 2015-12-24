#!/usr/bin/python
# -*- coding: utf-8 -*-
from app import app, mongo, db, mongoClientDB
from flask import jsonify, request
from bson.objectid import ObjectId
from collections import OrderedDict
from bson import json_util
import json,copy,binascii,os

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
  def __init__(self, answer_type, answer, answer_range, score):
    self.answer_type = answer_type
    self.answer = answer
    self.answer_range = answer_range
    self.score = score
  def to_dict(self):
    return dict(
        answer_type=self.answer_type,
        answer=self.answer,
        answer_range = self.answer_range,
        score = self.score
      )

# 保存实验报告
@app.route('/report', methods=['POST'])
def save_report():
  form = json.loads(request.data,object_pairs_hook=OrderedDict)
  form["status"] = "uncommitted"

  ids_dict = copy.copy(form)
  ids_dict.pop("report")

  query_report = mongo.db.reports.find_one(ids_dict)
  if query_report and query_report["status"] == "committed":
    return jsonify(BaseResult("801","无法修改已经提交的报告").to_dict())

  if query_report:
    form["_id"] = query_report["_id"]
  mongo.db.reports.save(form)

  form.pop("_id")
  return jsonify(BaseResult("200",form).to_dict())

# 获取实验报告
@app.route('/report/<student_id>/<class_id>/<experiment_id>', methods=['GET'])
def get_report(student_id, class_id,experiment_id):
  query = get_query(student_id,class_id,experiment_id)
  query_report = mongo.db.reports.find_one(query)

  if not query_report:
    return jsonify(BaseResult("404","Not Found").to_dict())

  query_report.pop("_id")
  return jsonify(BaseResult("200",query_report).to_dict())

# --插入实验报告模板
@app.route('/report/template/<experiment_id>', methods=['POST'])
def add_template(experiment_id):
  result = mongo.db.templates.find_one({"experiment_id":experiment_id})
  form = json.loads(request.data, object_pairs_hook=OrderedDict)
  if not result:
    form['experiment_id'] = experiment_id
  else:
    form['_id'] = result['_id']
  mongo.db.templates.save(form)
  return json_util.dumps(form)

# 获取实验报告模板
@app.route('/report/template/<experiment_id>', methods=['GET'])
def get_answer(experiment_id):
  result = mongo.db.templates.find_one({"experiment_id":experiment_id})
  if not result:
    return jsonify(BaseResult("404","Not Found").to_dict())
  return jsonify(BaseResult("200",result["template"]).to_dict())

# --插入答案
@app.route('/report/answer/<experiment_id>', methods=['POST'])
def add_answer(experiment_id):
  result = mongo.db.answers.find_one({"experiment_id":experiment_id})
  form = json.loads(request.data, object_pairs_hook=OrderedDict)
  if not result:
    form['experiment_id'] = experiment_id
  else:
    form['_id'] = result['_id']
  mongo.db.answers.save(form)
  return json_util.dumps(form)

# 获取正确答案
@app.route('/report/answer/<experiment_id>', methods=['GET'])
def get_template(experiment_id):
  answer = mongo.db.answers.find_one({"experiment_id":"1"})
  #answer = mongo.db.answers.find_one({"experiment_id":experiment_id})
  if not answer:
    return jsonify(BaseResult("404","Not Found").to_dict())

  token = request.headers.get('token')
  #result = mongo.db.tokens.find_one({"experiment_id":experiment_id,"token":token})
  result = mongo.db.tokens.find_one({"experiment_id":"1","token":token})
  if not result:
    return jsonify(BaseResult("501","没有权限获取答案").to_dict())

  return jsonify(BaseResult("200",answer["report"]).to_dict())

# 提交实验报告并打分
@app.route('/report/<student_id>/<class_id>/<experiment_id>', methods=['POST'])
def submit_report(student_id, class_id, experiment_id):

  query = get_query(student_id,class_id,experiment_id)

  #获取有序的学生实验报告
  student_report_with_id = mongoClientDB['reports'].find_one(query)
  if not student_report_with_id:
    return jsonify(BaseResult("404","Not Found").to_dict())
  if student_report_with_id["status"] == "committed":
    return jsonify(BaseResult("110","无法重复提交实验报告").to_dict())
  student_report = student_report_with_id["report"]
  
  #获取有序的实验报告答案
  answer_report_with_id = mongoClientDB['answers'].find_one({"experiment_id":"1"})
  #answer_report_with_id = mongoClientDB['answers'].find_one({"experiment_id":query["experiment_id"]})
  if not answer_report_with_id:
    return jsonify(BaseResult("404","Not Found").to_dict())
  answer_report = answer_report_with_id["report"]

  #打分
  graded_report = grade(student_report, answer_report)

  query["report"] = graded_report
  query["status"] = "committed"
  query["_id"] = student_report_with_id["_id"]
  query["token"] = binascii.b2a_base64(os.urandom(24))[:-1]

  mongo.db.reports.save(query)
  #mongo.db.tokens.insert({"experiment_id":query["experiment_id"],"token":query["token"]})
  mongo.db.tokens.insert({"experiment_id":"1","token":query["token"]})

  query.pop("_id")
  return jsonify(BaseResult("200",query).to_dict())

#将student_id, class_id, experiment_id构造为dict类型的query
def get_query(student_id, class_id, experiment_id):
  query = {}
  query["student_id"] = student_id
  query["class_id"] = class_id
  query["experiment_id"] = experiment_id
  return query

#判断当前key是否为新的section
def is_new_section(key):
  if key[0].isdigit() and not(key[2].isdigit()):
    return True
  return False

# 根据answer_report批改student_report
def grade(student_report, answer_report):
  answers = []
  find_all_answers(answer_report, answers)
  answers.reverse()
  answers_bak = copy.copy(answers)

  section_total_score = [0]
  section_total_scores = []
  section_count = [0]
  section_counts = []
  total_score = [0]
  calculate_total_scores(answer_report, answers, section_total_score, section_total_scores, total_score, section_count, section_counts)

  answers = answers_bak
  section_score = [0]
  section_scores = []
  section_correct_count = [0]
  section_correct_counts = []
  final_score = [0]
  grade_all_answers(student_report, answers, section_score, section_scores, final_score, section_correct_count, section_correct_counts)

  section_scores.pop(0)
  section_total_scores.pop(0)
  section_counts.pop(0)
  section_correct_counts.pop(0)

  student_report["section_total_scores"] = section_total_scores
  student_report["total_score"] = total_score[0]
  student_report["section_scores"] = section_scores
  student_report["final_score"] = final_score[0]
  student_report["section_counts"] = section_counts
  student_report["section_correct_counts"] = section_correct_counts

  return student_report

# 根据顺序的answers批改student_report
def grade_all_answers(node, answers, section_score, section_scores, final_score, section_correct_count, section_correct_counts):
  if isinstance(node, dict) :
    for x in range(len(node)):
      temp_key = node.keys()[x]
      temp_value = node[temp_key]
      #print temp_key
      if is_new_section(temp_key):
        section_scores.append(section_score[0])
        final_score[0] += section_score[0]
        section_score = [0]
        section_correct_counts.append(section_correct_count[0])
        section_correct_count[0] = 0
      if temp_key == 'answer':
        answer = answers.pop()
        #print answer.answer
        if answer.answer_type == 'fill-in-the-blank':
          print temp_value
          lower_bound = answer.answer - answer.answer_range
          upper_bound = answer.answer + answer.answer_range
          #print lower_bound, upper_bound
          if temp_value and lower_bound <= float(temp_value) <= upper_bound:
            node["score"] = answer.score
            section_correct_count[0] = section_correct_counts[0] +1
          else:
            node["score"] = 0
        else:
          if temp_value == answer.answer:
            node["score"] = answer.score
            section_correct_count[0] = section_correct_counts[0] +1
          else:
            node["score"] = 0
        section_score[0] += node["score"]
        if len(answers) ==0:
          section_scores.append(section_score[0])
          final_score[0] += section_score[0]
          section_score = [0]
          section_correct_counts.append(section_correct_count[0])
          section_correct_count[0] = 0
      grade_all_answers(temp_value, answers, section_score, section_scores, final_score, section_correct_count, section_correct_counts)
  if isinstance(node, list) :
    for x in node:
      grade_all_answers(x, answers, section_score, section_scores, final_score, section_correct_count, section_correct_counts)

# 计算每部分分数和总分
def calculate_total_scores(node, answers, section_total_score, section_total_scores, total_score, section_count, section_counts):
  if isinstance(node, dict) :
    for x in range(len(node)):
      temp_key = node.keys()[x]
      temp_value = node[temp_key]
      #print temp_key
      if is_new_section(temp_key):
        section_total_scores.append(section_total_score[0])
        total_score[0] += section_total_score[0]
        section_total_score = [0]
        section_counts.append(section_count[0])
        section_count = [0]
      if temp_key == 'answer':
        section_count[0] = section_count[0] + 1
        answer = answers.pop()
        #print answer.answer
        section_total_score[0] += node["score"]
        if len(answers) ==0:
          section_total_scores.append(section_total_score[0])
          total_score[0] += section_total_score[0]
          section_total_score = [0]
          section_counts.append(section_count[0])
          section_count = [0]
      calculate_total_scores(temp_value, answers, section_total_score, section_total_scores, total_score, section_count, section_counts)
  if isinstance(node, list) :
    for x in node:
      calculate_total_scores(x, answers, section_total_score, section_total_scores, total_score, section_count, section_counts)

# 将answer_report中的所有answer按顺序存入answers, 并计算section_total_scores
def find_all_answers(node, answers):
  if isinstance(node, dict) :
    for x in range(len(node)):
      temp_key = node.keys()[x]
      temp_value = node[temp_key]
      #print temp_key
      if temp_key == 'answer':
        answer = temp_value
        answer_type = node['type']
        score = node['score']
        if answer_type == 'fill-in-the-blank':
          answer_range = node['range']
          #print answer_type, answer, answer_range, score
          answers.append(Answer(answer_type, answer, answer_range,score))
        else:
          #print answer_type, answer, score
          answers.append(Answer(answer_type, answer, 0, score))
      find_all_answers(temp_value, answers)
  if isinstance(node, list) :
    for x in node:
      find_all_answers(x, answers)
