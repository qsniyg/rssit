# -*- coding: utf-8 -*-


import importlib
import rssit.util
import rssit.generators.instagram
import rssit.generators.twitter
import rssit.generators.vine
import rssit.generators.flickr
import rssit.generators.weibo
import rssit.generators.facebook
import rssit.generators.soundcloud
import rssit.generators.tumblr
import rssit.generators.tistory
import rssit.generators.news


generator_list = [
    rssit.generators.instagram,
    rssit.generators.twitter,
    rssit.generators.vine,
    rssit.generators.flickr,
    rssit.generators.weibo,
    rssit.generators.facebook,
    rssit.generators.soundcloud,
    rssit.generators.tumblr,
    rssit.generators.tistory,
    rssit.generators.news
]

generator_dict = {}


def build_dict():
    rssit.util.build_all_dict(generator_list, generator_dict)


def update():
    for i in generator_list:
        importlib.reload(i)

    build_dict()
