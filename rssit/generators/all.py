# -*- coding: utf-8 -*-


import importlib

import rssit.generators.instagram
import rssit.generators.twitter
import rssit.generators.vine
import rssit.generators.flickr
import rssit.generators.brackify


all_generators = [
    rssit.generators.instagram,
    rssit.generators.twitter,
    rssit.generators.vine,
    rssit.generators.flickr,
    rssit.generators.brackify
]


def update():
    for i in all_generators:
        importlib.reload(i)
