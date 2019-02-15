#!/usr/bin/env python
# -*- coding:utf-8 -*-
# _AUTHOR_  : zhujingxiu
# _DATE_    : 2019/2/13
import redis
import json
import os
import xlrd
import csv
from web.models import Account, EnrolledCourse, CourseSection, EnrolledDegreeCourse


class DataRefresh(object):

    def __init__(self, data_dir):
        self.redis = redis.Redis(host='127.0.0.1', port=6379)
        self.data_dir = data_dir

    def run(self):
        if os.path.exists(self.data_dir):
            for _curfile in os.listdir(self.data_dir):
                if os.path.isdir(_curfile):
                    continue
                filename = os.path.basename(_curfile)
                if not filename.startswith('viewlogs') and not filename.endswith('.csv'):
                    continue
                day = _curfile.split('@')[-1].split('.')[0]
                data_dict = self.read_csv_file('/'.join([self.data_dir, filename]), day)
                # print(filename, ' 行数：%d, 列数： %d' % row_col)

    def read_csv(self, file):
        print(file)
        nrows , ncols = 0, 0
        try:
            data = xlrd.open_workbook(file)
            table = data.sheet_by_index(0)
            nrows = table.nrows  # 获取该sheet中的有效行数
            ncols = table.ncols  # 获取列表的有效列数
        except Exception as e:
            print(e)

        return nrows, ncols

    def read_csv_file(self, filename, day):
        file_lines = {}
        day = ''.join(day.split('-'))
        with open(filename) as f:
            reader = csv.DictReader(f)
            for index, row in enumerate(reader, 1):
                if len(row) != 13:
                    continue

                data = self.parse_csv_line(row)
                if not data:
                    continue
                item = {
                    "vid": data.get('vid'),
                    "title": data.get('title'),
                    "course_title": data.get('course_title'),
                    "degree_course": data.get('degree_course'),
                    "ip_addr": data.get('ip_addr'),
                    "location": data.get('location'),
                    "play_limit": data.get('play_limit'),
                    "play_place": data.get('play_place'),
                    "total": data.get('total'),
                    "start_time": data.get('start_time'),
                }
                key = '%s-%s-%s-%s' % (data.get('uid'), data.get('course_type'), data.get('course_id'), day)
                self.redis.lpush(key, json.dumps(item))
                if file_lines.get(key):
                    file_lines[key].append(item)
                else:
                    file_lines[key] = [item]
        print('*'*100)
        print(day, file_lines)
        return file_lines

    def parse_csv_line(self, row):
        vid = row.get('视频ID')
        title = row.get('视频标题')
        uid = row.get('自定义ID')
        ip_addr = row.get('IP地址')
        location = row.get('观众地理位置')
        play_limit = row.get('观看时长')
        flow = row.get('消耗流量')
        client = row.get('播放终端')
        system = row.get('操作系统')
        browser = row.get('浏览器')
        play_place = row.get('观看地址')
        start_time = row.get('开始时间')
        params = self.parse_url(play_place)

        account = self.get_account(uid, params.get('enrolled_course_id'))

        if not account:
            return False
        section = self.get_course_section(vid, params.get('course_section_id'))
        if not section:
            return False
        course = section.chapter.course
        memo = self.get_memo(account.uid, params.get('enrolled_course_id'))
        data = {
            'uid': account.uid,
            'course_type': int(course.course_type == 2),
            'course_id': course.pk,
            'course_title': course.name,
            'degree_course': course.degree_course.name if course.degree_course else '',
            "vid": vid,
            "title": title if title else section.name,
            "ip_addr": ip_addr,
            "play_limit": play_limit,
            "play_place": play_place,
            "total": section.video_time,
            "location": location,
            "start_time": start_time
        }
        return data

    def get_account(self, uid=None, enrolled_course_id=None):
        if not uid and not enrolled_course_id:
            return False
        if uid:
            account = Account.objects.filter(uid=uid).first()
        elif enrolled_course_id:
            account = EnrolledCourse.objects.filter(pk=enrolled_course_id).first().account
        else:
            account = None

        if self.check_account(account):
            return False
        return account

    def check_account(self, account):
        if not account or not isinstance(account, dict):
            return False
        if not account.get('username'):
            return False
        return True

    def parse_url(self, url):
        '''
        1、https://www.luffycity.com/micro/play/6803/18044
        描述：6803为`CourseSection`表中的`id`字段，18044为`StudyRecord`表中的 `ID` （注：该ID有的可能没有）
        2、https://www.luffycity.com/classmate/play/678/6442
        描述：678为`CourseSection`表中的`id`字段，6442为`EnrolledCourse` 表中的 `ID`（注：该ID有的可能没有）
        3、https://www.luffycity.com/course/video/43/2976/CourseChapter
        描述：43为`Course`表中的`id`字段，2976为`CourseSection`表中的`ID`
        4、https://www.luffycity.com/course/video/7/31/FreeCourse
        描述：7为`Course`表中的`id`字段，31为`CourseSection`表中的`ID`
        5、https://m.luffycity.com/study/video/841
        描述：841为`CourseSection`表中的`ID`
        :param url:
        :return:
        '''
        data = {}
        if not url or not (url.startswith('https://www.luffycity.com') or url.startswith('https://m.luffycity.com')):
            return data
        url = url.lower()
        if url.find('/micro/play/') != -1:
            params = url.split('/')
            if params[-2].isnumeric():
                data['course_section_id'] = params[-2]
                data['study_record_id'] = params[-1] if params[-1].isnumeric() else 0
            else:
                data['course_section_id'] = params[-1] if params[-1].isnumeric() else 0
        if url.find('/classmate/play/') != -1:
            params = url.split('/')
            if params[-2].isnumeric():
                data['course_section_id'] = params[-2]
                data['enrolled_course_id'] = params[-1] if params[-1].isnumeric() else 0
            else:
                data['course_section_id'] = params[-1] if params[-1].isnumeric() else 0
        if url.find('/course/video/') != -1 and url.endswith('coursechapter'):
            params = url.split('/')
            data['course_id'] = params[-3] if params[-3].isnumeric() else 0
            data['course_section_id'] = params[-2] if params[-2].isnumeric() else 0
        if url.find('/course/video/') != -1 and url.endswith('freecourse'):
            params = url.split('/')
            data['course_id'] = params[-3] if params[-3].isnumeric() else 0
            data['course_section_id'] = params[-2] if params[-2].isnumeric() else 0
        if url.startswith('https://m.luffycity.com/study/video/'):
            data['course_section_id'] = url.split('/')[-1] if url.split('/')[-1].isnumeric() else 0

        return data

    def get_course_section(self, video_id, course_section_id):
        '''
        可根据视频VID以及观看地址上的课时ID确定课程为学位课还是专题课
        :return:
        '''
        section = CourseSection.objects.filter(section_link=video_id, pk=course_section_id).first()
        if not section:
            return False
        return section

    def get_memo(self, uid, enrolled_course_id):
        enrolled_degree_course = EnrolledDegreeCourse.objects.filter(account__uid=uid, pk=enrolled_course_id).first()
        if not enrolled_degree_course:
            return False
        account = enrolled_degree_course.account
        return account