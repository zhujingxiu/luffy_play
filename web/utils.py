#!/usr/bin/env python
# -*- coding:utf-8 -*-
# _AUTHOR_  : zhujingxiu
# _DATE_    : 2019/2/19
import time


def formater_second(time_str):
    if not time_str or time_str.find(':') == -1:
        return 0
    time_arr = time_str.split(':')
    pow_val = 0
    sum_val = 0
    for i in reversed(time_arr):
        sum_val += int(i) * (60 ** pow_val)
        pow_val += 1
    return sum_val


def formater_day(datetime_str, formatter=None):

    if not datetime_str:
        return ''
    chk_arr = datetime_str.replace('/', '-').split(':')
    if len(chk_arr) <= 2:
        chk_arr.append('00')
    time_struct = time.strptime(':'.join(chk_arr), "%Y-%m-%d %H:%M:%S")
    time_stamp = int(time.mktime(time_struct))
    if not formatter:
        return time_stamp
    if formatter:
        return time.strftime(formatter, time.localtime(time_stamp))

