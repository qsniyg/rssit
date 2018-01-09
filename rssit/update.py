# -*- coding: utf-8 -*-


import importlib

import rssit.config

modules = []


def set_modules():
    global modules
    modules = [
        rssit.config,
        rssit.converter,
        rssit.converters.all,
        rssit.formats,
        rssit.generator,
        rssit.generators.all,
        rssit.path,
        rssit.paths.all,
        rssit.serializer,
        rssit.serializers.all,
        rssit.util,
        rssit.http,
        rssit.globals,
        rssit.__main__
    ]


def update_module(module):
    importlib.reload(module)

    if hasattr(module, "update"):
        module.update()


def kill_module(module):
    if hasattr(module, "unload"):
        module.unload()


def update():
    set_modules()
    for module in modules:
        update_module(module)


def kill():
    set_modules()
    for module in modules:
        kill_module(module)
