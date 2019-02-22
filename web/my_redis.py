#!/usr/bin/env python
# -*- coding:utf-8 -*-
# _AUTHOR_  : zhujingxiu
# _DATE_    : 2019/2/19
import redis


class MyRedis(redis.Redis):

    def list_range_iter(self, key, count=20):
        index = 0
        while True:
            data_list = self.lrange(key, index, index + count -1)
            if not data_list:
                return
            index += count
            for item in data_list:
                yield item
