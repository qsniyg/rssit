# -*- coding: utf-8 -*-


import rssit.serializers.all


def process(config, data, format):
    sd = rssit.serializers.all.serializer_dict

    if format not in sd:
        return data

    return sd[format]["process"](config, data)
