# -*- coding: utf-8 -*-


import importlib

import rssit.generate
import rssit.config
import rssit.util
import rssit.http


def update():
    importlib.reload(rssit.generate)
    rssit.generate.update()

    importlib.reload(rssit.config)
    importlib.reload(rssit.util)
    importlib.reload(rssit.http)
