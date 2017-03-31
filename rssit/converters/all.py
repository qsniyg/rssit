# -*- coding: utf-8 -*-


import importlib
import rssit.converters.social_to_social
import rssit.converters.social_to_feed
import rssit.converters.feed_to_rssatom


converters_list = [
    rssit.converters.social_to_social,
    rssit.converters.social_to_feed,
    rssit.converters.feed_to_rssatom
]

converters_dict = {}


def build_dict():
    for converter in converters_list:
        for info in converter.infos:
            if not info["input"] in converters_dict:
                converters_dict[info["input"]] = {}

            converters_dict[info["input"]][info["output"]] = info


def update():
    for i in converters_list:
        importlib.reload(i)

    build_dict()
