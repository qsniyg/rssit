# -*- coding: utf-8 -*-


import rssit.serializers.all


def process(data, format):
    sd = rssit.serializers.all.serializers_dict

    if format not in sd:
        return data

    return sd[format]["process"](data)
