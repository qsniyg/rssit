# -*- coding: utf-8 -*-


import importlib

import rssit.generate
import rssit.config
import rssit.util
import rssit.http


def update_module(module):
    importlib.reload(module)

    if hasattr(module, "update"):
        module.update()


def update():
    update_module(rssit.config)
    update_module(rssit.converter)
    update_module(rssit.converters.all)
    update_module(rssit.formats)
    update_module(rssit.generator)
    update_module(rssit.generators.all)
    update_module(rssit.path)
    update_module(rssit.paths.all)
    update_module(rssit.serializer)
    update_module(rssit.serializers.all)
    update_module(rssit.util)
    update_module(rssit.http)
    update_module(rssit.globals)
    update_module(rssit.__main__)
