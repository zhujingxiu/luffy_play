from django.urls import reverse
from django.http import JsonResponse
from django.views.generic import TemplateView, View
from django.template.loader import render_to_string
from .data_refresh import DataRefresh
from . import models
import redis
import json

red = redis.Redis(host='127.0.0.1', port=6379)


class IndexView(TemplateView):
    template_name = 'management/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        # 此处编写你的代码
        #
        return context


class StudyRecordView(TemplateView):
    template_name = 'management/study-record.html'

    def get_context_data(self, **kwargs):
        context = super(StudyRecordView, self).get_context_data(**kwargs)
        # 此处编写你的代码
        #
        return context


class AccountStudyRecordView(View):
    def get(self, request):
        username = request.GET.get('username')
        print(username)
        users = models.Account.objects.filter(username__contains=username)
        if not users:
            return JsonResponse({'errCode': 1, 'total': 0, 'rows': {}})
        accounts = []
        for user in users:
            result = red.keys('%s*' % user.uid)
            if not result:
                continue
            for i in result:
                items = red.lrange(i, 0, -1)
                for item in items:
                    item = json.loads(item.decode())
                    item['user'] = user.username
                    item['uid'] = user.uid
                    item['user_link'] = reverse('study-count', kwargs={'uid': user.uid})
                    accounts.append(item)
        return JsonResponse({'errCode': 0, 'total': len(accounts), 'rows': accounts})


class DataRefreshView(View):

    def get(self, request):
        import time
        now_timestramp = int(time.time())
        now_datetime = time.strftime('%Y-%m-%d %H:%M:%S')

        last_time = red.get('last-data-refresh-time') or 0
        if last_time:
            print(last_time, type(last_time))
            # if now_timestramp - last_time < 30*60:
            #     return JsonResponse({'errCode': 1, 'msg': '上次清洗时间间隔太短了，请稍后再试'})
            last_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(last_time)))
        dr = DataRefresh('static/data/record/')
        files = dr.data_files()
        tpl = render_to_string('management/data-refresh.html',
                               {'last_time': last_time, 'files': files},
                               request=request)
        return JsonResponse({'errCode': 0, 'title': '准备执行数据清洗', 'tpl': tpl})

    def post(self, request):
        import time
        nowtime = int(time.time())
        red.set('last-data-refresh-time', nowtime)
        dr = DataRefresh('static/data/record/')
        data = dr.run()
        return JsonResponse({'errCode': 0, 'msg': nowtime})


class StudyCountView(TemplateView):
    template_name = 'management/study-count.html'

    def get_context_data(self, **kwargs):
        context = super(StudyCountView, self).get_context_data(**kwargs)
        # 此处编写你的代码
        uid = context.get('uid')
        print(uid)
        user = models.Account.objects.filter(uid=uid)
        if not user:
            return JsonResponse({'errCode': 1, 'msg': '用户不存在'})
        records = red.keys('%s*' % uid)
        for i in records:
            items = red.lrange(i, 0, -1)
            for item in items:
                item = json.loads(item.decode())
                print(item)
        return context

