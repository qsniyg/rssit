# -*- coding: utf-8 -*-


import rssit.update
import rssit.paths.home
import rssit.paths.reload
import rssit.paths.update
import rssit.paths.feed
import rssit.paths.notfound


paths_list = [
    rssit.paths.home,
    rssit.paths.reload,
    rssit.paths.update,
    rssit.paths.feed,
    rssit.paths.notfound
]

paths_dict = {}


def build_dict():
    for path in paths_list:
        for info in path.infos:
            paths_dict[info["path"].lower()] = info

build_dict()


def update():
    for i in paths_list:
        rssit.update.update_module(i)

    build_dict()
