# -*- coding: utf-8 -*-


import importlib
import rssit.util
import rssit.serializers.socialfeed


serializer_list = [
    rssit.serializers.socialfeed
]

serializer_dict = {}


def build_dict():
    rssit.util.build_all_dict(serializer_list, serializer_dict)


def update():
    for i in serializer_list:
        importlib.reload(i)

    build_dict()
