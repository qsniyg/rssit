# -*- coding: utf-8 -*-


import importlib

import rssit.generate
import rssit.config
import rssit.util


def update():
    importlib.reload(rssit.generate)
    rssit.generate.update()

    importlib.reload(rssit.config)
    importlib.reload(rssit.util)
