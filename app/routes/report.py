#!/usr/bin/python
# -*- coding: utf-8 -*-
from app import app, mongo, db, mongoClientDB
from flask import jsonify, request
from bson.objectid import ObjectId
from collections import OrderedDict
from bson import json_util
import json,copy,binascii,os,re

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

# 全局变量
  global section_total_score
  global section_total_scores
  global section_count
  global section_counts
  global total_score

  global section_score
  global section_scores
  global section_correct_count
  global section_correct_counts
  global final_score

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

# --清空report和token
@app.route('/report/clear', methods=['DELETE'])
def clear():
  mongo.db.reports.remove()
  mongo.db.tokens.remove()
  return jsonify(BaseResult("200","删除成功！").to_dict())

# 保存实验报告
@app.route('/report', methods=['POST'])
def save_report():
  form = json.loads(request.data,object_pairs_hook=OrderedDict)

  ids_dict = copy.copy(form)
  ids_dict.pop("report")

  query_report = mongo.db.reports.find_one(ids_dict)
  if query_report and query_report["status"] == "committed":
    return jsonify(BaseResult("801","无法修改已经提交的报告").to_dict())

  if query_report:
    form["_id"] = query_report["_id"]
    form["status"] = "uncommitted"
  else:
    form["status"] = "uncommitted"

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

# 获取实验报告模板
@app.route('/report/template/<experiment_id>', methods=['GET'])
def get_answer(experiment_id):
  result = mongo.db.templates.find_one({"experiment_id":experiment_id})
  if not result:
    return jsonify(BaseResult("404","Not Found").to_dict())
  return jsonify(BaseResult("200",result["template"]).to_dict())

# 获取正确答案
@app.route('/report/answer/<experiment_id>', methods=['GET'])
def get_template(experiment_id):
  #answer = mongo.db.answers.find_one({"experiment_id":"1"})
  answer = mongo.db.answers.find_one({"experiment_id":experiment_id})
  if not answer:
    return jsonify(BaseResult("404","Not Found").to_dict())

  token = request.headers.get('token')
  result = mongo.db.tokens.find_one({"experiment_id":experiment_id,"token":token})
  #result = mongo.db.tokens.find_one({"experiment_id":"1","token":token})
  if not result:
    return jsonify(BaseResult("501","没有权限获取答案").to_dict())

  return jsonify(BaseResult("200",answer["report"]).to_dict())

# 提交实验报告并打分
@app.route('/report/<student_id>/<class_id>/<experiment_id>', methods=['POST'])
def submit_report(student_id, class_id, experiment_id):

  #获取有序的学生实验报告
  query = get_query(student_id,class_id,experiment_id)
  student_report_with_id = mongoClientDB['reports'].find_one(query)

  if not student_report_with_id:
    return jsonify(BaseResult("404","Not Found").to_dict())
  if student_report_with_id["status"] == "committed":
    return jsonify(BaseResult("110","无法重复提交实验报告").to_dict())
  student_report = student_report_with_id["report"]
  
  #获取有序的实验报告答案
  #answer_report_with_id = mongoClientDB['answers'].find_one({"experiment_id":"1"})
  answer_report_with_id = mongoClientDB['answers'].find_one({"experiment_id":query["experiment_id"]})
  if not answer_report_with_id:
    return jsonify(BaseResult("404","Not Found").to_dict())
  answer_report = answer_report_with_id["report"]

  query["report"] = grade(student_report, answer_report)
  query["status"] = "committed"
  query["_id"] = student_report_with_id["_id"]
  query["token"] = binascii.b2a_base64(os.urandom(24))[:-1]

  mongo.db.reports.save(query)
  mongo.db.tokens.insert({"experiment_id":query["experiment_id"],"token":query["token"]})
  #mongo.db.tokens.insert({"experiment_id":"1","token":query["token"]})

  query.pop("_id")
  return jsonify(BaseResult("200",query).to_dict())

#将student_id, class_id, experiment_id构造为dict类型的query
def get_query(student_id, class_id, experiment_id):
  query = {}
  query["student_id"] = student_id
  query["class_id"] = class_id
  query["experiment_id"] = experiment_id
  return query

# 根据answer_report批改student_report
def grade(student_report, answer_report):
  answers = []
  find_all_answers(answer_report, answers)
  answers.reverse()
  answers_bak = copy.copy(answers)

  global section_total_score
  section_total_score = [0]
  global section_total_scores
  section_total_scores = []
  global section_count
  section_count = [0]
  global section_counts
  section_counts = []
  global total_score
  total_score = [0]

  calculate_total_scores(answer_report, answers)

  global section_score
  section_score = [0]
  global section_scores
  section_scores = []
  global section_correct_count
  section_correct_count = [0]
  global section_correct_counts
  section_correct_counts = []
  global final_score
  
  final_score = [0]
  answers = answers_bak
  grade_all_answers(student_report, answers)

  # 由于index0位置的type是date而非section，注掉以下代码恰好可以保证section数组位置与content数组位置的对应
  # # 去除第一次遇到section时所添加的数据，第二次遇到section时获取的才是第一个section需要的数据
  #section_total_scores.remove(0)
  #section_scores.remove(0)
  #section_counts.remove(0)
  #section_correct_counts.remove(0)

  student_report["section_total_scores"] = section_total_scores
  student_report["total_score"] = total_score[0]
  student_report["section_scores"] = section_scores
  student_report["final_score"] = final_score[0]
  student_report["section_counts"] = section_counts
  student_report["section_correct_counts"] = section_correct_counts

  return student_report

# 根据顺序的answers批改student_report
def grade_all_answers(node, answers):
  global section_score
  global section_scores
  global section_correct_count
  global section_correct_counts
  global final_score
  if isinstance(node, dict) :
    for x in range(len(node)):
      temp_key = node.keys()[x]
      temp_value = node[temp_key]
      #print temp_key
      if temp_key == 'type' and temp_value == 'section':
        #print node["text"]
        #print "new",section_score,section_correct_count
        section_scores.append(section_score[0])
        final_score[0] += section_score[0]
        section_score = [0]
        section_correct_counts.append(section_correct_count[0])
        section_correct_count[0] = 0
      if temp_key == 'answer':
        answer = answers.pop()
        #print answer.answer
        if answer.answer_type == 'fill-in-the-blank':
          #print 'fill',temp_value, answer.answer, answer.answer_range
          if str(answer.answer_range)[len(str(answer.answer_range))-1] == '%':
            if(answer.answer >=0):
              lower_bound = answer.answer - answer.answer * float(answer.answer_range.replace('%','')) * 0.01
              upper_bound = answer.answer + answer.answer * float(answer.answer_range.replace('%','')) * 0.01
            else:
              lower_bound = answer.answer + answer.answer * float(answer.answer_range.replace('%','')) * 0.01
              upper_bound = answer.answer - answer.answer * float(answer.answer_range.replace('%','')) * 0.01
          else:
            lower_bound = answer.answer - answer.answer_range
            upper_bound = answer.answer + answer.answer_range
          if temp_value:
            try:
              #print temp_value
              temp_value_float = float(temp_value)
              #if temp_value and lower_bound <= temp_value_float <= upper_bound:
              if lower_bound <= temp_value_float <= upper_bound:
                node["score"] = answer.score
                section_correct_count[0] += 1
              else:
                node["score"] = 0
            except ValueError:
              print "Not a number!"
              node["score"] = 0
          else:
            node["score"] = 0
        else:
          #print 'choice',temp_value, answer.answer
          if temp_value == answer.answer: 
            node["score"] = answer.score
            section_correct_count[0] += 1
          else:
            node["score"] = 0
        section_score[0] += node["score"]
        if len(answers) ==0:
          section_scores.append(section_score[0])
          final_score[0] += section_score[0]
          section_score = [0]
          section_correct_counts.append(section_correct_count[0])
          section_correct_count[0] = 0
      grade_all_answers(temp_value, answers)
  if isinstance(node, list) :
    for x in node:
      grade_all_answers(x, answers)

# 计算每部分分数和总分
def calculate_total_scores(node, answers):
  global section_total_score
  global section_total_scores
  global section_count
  global section_counts
  global total_score
  if isinstance(node, dict) :
    for x in range(len(node)):
      temp_key = node.keys()[x]
      temp_value = node[temp_key]
      if temp_key == 'type' and temp_value == 'section':
        section_total_scores.append(section_total_score[0])
        total_score[0] += section_total_score[0]
        section_total_score = [0]
        section_counts.append(section_count[0])
        section_count = [0]
      if temp_key == 'answer':
        section_count[0] += 1
        answer = answers.pop()
        #print answer.answer,answer.score
        section_total_score[0] += answer.score
        #print section_count,section_total_score
        if len(answers) ==0:
          section_total_scores.append(section_total_score[0])
          total_score[0] += section_total_score[0]
          section_total_score = [0]
          section_counts.append(section_count[0])
          section_count = [0]
      calculate_total_scores(temp_value, answers)
  if isinstance(node, list) :
    for x in node:
      calculate_total_scores(x, answers)

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
