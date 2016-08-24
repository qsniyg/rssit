# -*- coding: utf-8 -*-


import rssit.generators.all
import importlib

from feedgen.feed import FeedGenerator


def process_feed(result, config):
    fg = FeedGenerator()

    fg.title(result["title"])

    if "description" in result:
        fg.description(result["description"])
    else:
        fg.description(result["title"])

    if "id" in result:
        fg.id(result["id"])
    else:
        fg.id(config["url"])

    if "url" in result:
        fg.link(result["url"])
    else:
        fg.link(href=config["url"], rel="alternate")


    for entry in result["entries"]:
        fe = fg.add_entry()

        fe.link(href=entry["url"], rel="alternate")

        if "id" in entry:
            fe.id(entry["id"])
        else:
            fe.id(entry["url"])

        fe.title(entry["title"])

        if "description" in entry:
            fe.description(entry["description"])
        else:
            fe.description(entry["title"])

        fe.author(name=entry["author"])
        fe.published(entry["date"])
        fe.content(entry["content"], type="html")


    if config["type"] == "atom":
        return fg.atom_str(encoding="ascii")
    elif config["type"] == "rss":
        return fg.rss_str(encoding="ascii")


def process(config, path):
    for generator in rssit.generators.all.all_generators:
        result = generator.generate(config, path)

        if result == None:
            continue

        if config["brackets"]:
            result["title"] = "[%s] %s" % (generator.info["name"],
                                           result["title"])

        if config["type"] == "atom" or config["type"] == "rss":
            return process_feed(result, config)
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
