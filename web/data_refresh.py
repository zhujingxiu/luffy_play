#!/usr/bin/env python
# -*- coding:utf-8 -*-
# _AUTHOR_  : zhujingxiu
# _DATE_    : 2019/2/13
from .my_redis import MyRedis
import json
import os
import xlrd
import csv
from web.models import Account, EnrolledCourse, CourseSection, EnrolledDegreeCourse


class DataRefresh(object):

    def __init__(self, data_dir):
        self.__redis = MyRedis('127.0.0.1')
        self.data_dir = data_dir
        self.__redis.set('current_reading', '')
        self.__redis.set('reading_number', 0)
        self.__redis.set('read_all', 0)
        self.__redis.ltrim('read_files', 1, 0)

    def data_files(self):
        data = []
        if not os.path.exists(self.data_dir):
            return data
        for _curfile in os.listdir(self.data_dir):
            if os.path.isdir(_curfile):
                continue
            filename = os.path.basename(_curfile)
            if not filename.startswith('viewlogs') and not filename.endswith('.csv'):
                continue
            day = _curfile.split('@')[-1].split('.')[0]
            data.append({'name': _curfile, 'day': day, 'path': '/'.join([self.data_dir, filename])})
        return data

    def run(self):
        if not self.data_files():
            return False
        self.__redis.set('read_all', len(self.data_files()))
        for item in self.data_files():
            self.__redis.set('current_reading', '%s|%s' % (item.get('name'), item.get('day')))
            self.__redis.incr('reading_number')
            data_line = self.read_csv_file(item.get('path'), item.get('day'))
            print(item.get('day'),data_line)
            self.__redis.lpush('read_files', json.dumps({'key': item.get('day'), 'val': len(data_line.keys())}))
        self.__redis.set('read_all', -1)

    def read_csv_file(self, filename, day):
        file_lines = {}
        day = day.replace('-', '')
        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if len(row) != 13:
                    continue

                data = self.parse_csv_line(row)
                if not data:
                    continue
                item = {
                    "vid": data.get('vid'),
                    "title": data.get('title'),
                    "mentor": data.get('mentor'),
                    "degree_course": data.get('degree_course'),
                    "ip_addr": data.get('ip_addr'),
                    "location": data.get('location'),
                    "play_limit": data.get('play_limit'),
                    "play_place": data.get('play_place'),
                    "total": data.get('total'),
                    "start_time": data.get('start_time'),
                }
                key = '%s-%s-%s-%s' % (data.get('uid'), data.get('course_type'), data.get('course_id'), day)
                self.__redis.lpush(key, json.dumps(item))
                if file_lines.get(key):
                    file_lines[key].append(item)
                else:
                    file_lines[key] = [item]
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
        course_section = self.get_course_section(vid, params.get('course_section_id'))
        if not course_section:
            return False
        mentor = self.get_mentor(account, course_section)
        course = course_section.chapter.course
        data = {
            "vid": vid,
            "uid": account.uid,
            "mentor": mentor.username if mentor else '',
            "course_id": course.pk,
            "course_type": int(course.course_type == 2),
            "degree_course": course.degree_course.name if course.degree_course else '',
            "title": title if title else course_section.name,
            "ip_addr": ip_addr,
            "play_limit": play_limit,
            "play_place": play_place,
            "total": course_section.video_time,
            "location": location,
            "start_time": start_time
        }
        return data

    def get_account(self, uid=None, enrolled_course_id=None):
        account = None
        if not uid and not enrolled_course_id:
            return account
        if uid:
            account = Account.objects.filter(uid=uid).first()
        elif enrolled_course_id:
            entity = EnrolledCourse.objects.filter(pk=enrolled_course_id).first()
            if entity:
                account = entity.account

        if self.check_account(account):
            return None
        return account

    def check_account(self, account):
        if not account or not isinstance(account, Account):
            return False
        if not account.username:
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
        格式固定，避免使用开销较大的正则匹配
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

        return section

    def get_mentor(self, account, course_section):
        '''
        可根据⾃定义ID以及观看地址上的报名记录ID确定导师
        or
        EnrolledDegreeCourse
            unique_together = ('account', 'degree_course')
        :param uid:
        :param course_section:
        :return:
        '''
        if not account or not course_section:
            return None
        degree_course = course_section.chapter.course.degree_course
        enrolled_degree_course = EnrolledDegreeCourse.objects.filter(account=account,
                                                                     degree_course=degree_course).first()
        if not enrolled_degree_course:
            return None

        mentor = enrolled_degree_course.mentor
        return mentor
