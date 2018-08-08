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
import rssit.generators.xe
import rssit.generators.naverblog
import rssit.generators.reddit
import rssit.generators.livedoor
import rssit.generators.bastar
import rssit.generators.periscope

have_notifications = False
try:
    import dbus
    rssit.util.gobject.__dict__
    import rssit.generators.notifications
    have_notifications = True
except ImportError as e:
    print(e)
    print("Warning: one of dbus-python or gobject is missing, so no notification support")
    pass


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
    rssit.generators.news,
    rssit.generators.xe,
    rssit.generators.naverblog,
    rssit.generators.reddit,
    rssit.generators.livedoor,
    rssit.generators.bastar,
    rssit.generators.periscope
]

if have_notifications:
    generator_list.append(rssit.generators.notifications)

generator_dict = {}


def build_dict():
    rssit.util.build_all_dict(generator_list, generator_dict)


def update():
    for i in generator_list:
        importlib.reload(i)

    build_dict()
