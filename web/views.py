from django.urls import reverse
from django.http import JsonResponse
from django.views.generic import TemplateView, View
from django.template.loader import render_to_string
from .data_refresh import DataRefresh
from . import models, utils
from .my_redis import MyRedis
import json
my_red = MyRedis(host='127.0.0.1', port='6379',)


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
        if not username:
            return JsonResponse({'errCode': 1, 'total': 0, 'rows': {}})
        users = models.Account.objects.filter(username__contains=username)
        if not users:
            return JsonResponse({'errCode': 1, 'total': 0, 'rows': {}})
        accounts = {}
        for user in users:
            result = my_red.scan_iter('%s*' % user.uid, count=None)
            if not result:
                continue
            for _key in result:
                items = my_red.list_range_iter(_key)
                for item in items:
                    item = json.loads(item.decode())
                    item['RowId'] = _key.decode()
                    item['user'] = user.username
                    item['uid'] = user.uid
                    item['user_link'] = reverse('study-count', kwargs={'uid': user.uid})
                    accounts[item.get('start_time')] = item
        accounts = [item[1] for item in sorted(accounts.items(), key=lambda i: i[0])]
        return JsonResponse({'errCode': 0, 'total': len(accounts), 'rows': accounts})


class DataRefreshView(View):

    def get(self, request):

        progress = request.GET.get('progress')
        if progress:
            read_all = int(my_red.get('read_all').decode())
            if read_all == -1:
                return JsonResponse({'errCode': 0, 'msg': ''})
            doing_num = int(my_red.get('reading_number').decode())
            doing_item = my_red.get('current_reading').decode()
            read_files = my_red.list_range_iter('read_files')
            files = []
            for item in read_files:
                files.append(json.loads(item))

            rate = float('%.2f' % (doing_num/read_all*100.00))
            return JsonResponse({'errCode': 0, 'data': {'item': doing_item, 'progress': rate, 'read': files}})
        import time
        now_timestramp = int(time.time())
        now_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        last_time = my_red.get('last-data-refresh-time') or 0
        if last_time:
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
        my_red.set('last-data-refresh-time', nowtime)
        dr = DataRefresh('static/data/record/')
        data = dr.run()
        return JsonResponse({'errCode': 0, 'msg': nowtime})


class StudyCountView(TemplateView):
    template_name = 'management/study-count.html'

    def get_context_data(self, **kwargs):
        context = super(StudyCountView, self).get_context_data(**kwargs)
        # 此处编写你的代码

        return context

    def post(self, request, uid):
        user = models.Account.objects.filter(uid=uid).first()
        if not user:
            return JsonResponse({'errCode': 1, 'msg': '用户不存在'})
        records = my_red.scan_iter('%s-*' % uid)
        tmp = {}
        for i in records:
            items = my_red.list_range_iter(i)
            day_date = ''
            total_limit = 0
            for key in items:
                item = json.loads(key)

                second = utils.formater_second(item.get('play_limit'))
                total_limit += second
                day_date = item.get('start_time')
            new_day = utils.formater_day(day_date, formatter='%Y-%m-%d')
            tmp[new_day] = float('%.2f' % (total_limit / 60))

        data = sorted(tmp.items(), key=lambda i: i[0])
        data_day, data_minute = [], []
        for item in data:
            data_day.append(item[0])
            data_minute.append(item[1])
        return JsonResponse({'errCode': 0, 'data': {'user': user.username, 'day': data_day, 'minute': data_minute}})