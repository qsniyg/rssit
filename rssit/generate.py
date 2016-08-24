# -*- coding: utf-8 -*-


import rssit.generators.all
import importlib


def process(config, path):
    for generator in rssit.generators.all.all_generators:
        result = generator.generate(config, path)

        if result == None:
            continue

        if config["type"] == "atom":
            return result.atom_str(encoding="ascii")
        elif config["type"] == "rss":
            return result.rss_str(encoding="ascii")
        else:
            return None


def http(config, path, get):
    for generator in rssit.generators.all.all_generators:
        result = generator.http(config, path, get)

        if result == None:
            continue


def update():
    importlib.reload(rssit.generators.all)
    rssit.generators.all.update()
