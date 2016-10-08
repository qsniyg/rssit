# -*- coding: utf-8 -*-


import importlib
import rssit.util
import rssit.generators.instagram
import rssit.generators.twitter
import rssit.generators.vine
#import rssit.generators.flickr


generator_list = [
    rssit.generators.instagram,
    rssit.generators.twitter,
    rssit.generators.vine
    #rssit.generators.flickr
]

generator_dict = {}


def build_dict():
    rssit.util.build_all_dict(generator_list, generator_dict)

build_dict()


def update():
    for i in generator_list:
        importlib.reload(i)

    build_dict()
