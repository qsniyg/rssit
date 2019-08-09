# -*- coding: utf-8 -*-


appname = "rssit"

try:
    config
except NameError:
    config = {
        "model": {},
        "config": {}
    }

try:
    wblist_cache
except NameError:
    wblist_cache = {}
