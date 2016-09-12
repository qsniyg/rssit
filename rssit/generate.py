# -*- coding: utf-8 -*-


import rssit.generators.all
import importlib

from feedgen.feed import FeedGenerator


def find_generator(url):
    for generator in rssit.generators.all.all_generators:
        result = generator.check(url)

        if result:
            return generator


def social_to_regular(result, config):
    entries = []

    for entry in result["entries"]:
        caption = entry["caption"]

        if not caption:
            caption = "(n/a)"

        content = "<p><em>%s</em></p><p>%s</p>" % (
            entry["author"],
            caption.replace("\n", "<br />\n")
        )

        title = "%s: %s" % (
            entry["author"],
            caption.replace("\n", " ")
        )

        if entry["videos"]:
            for video in entry["videos"]:
                content += "<p><em>Click to watch video</em></p>"

                content += "<a href='%s'><img src='%s'/></a>" % (
                    video["video"],
                    video["image"]
                )

        if entry["images"]:
            for image in entry["images"]:
                content += "<p><img src='%s'/></p>" % image

        entries.append({
            "url": entry["url"],
            "title": title,
            "author": entry["author"],
            "date": entry["date"],
            "content": content
        })

    return entries


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


    entries = result["entries"]

    if "social" in result and result["social"]:
        entries = social_to_regular(result, config)


    for entry in entries:
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
        #fe.updated(entry["date"])
        fe.content(entry["content"], type="html")


    if config["type"] == "atom":
        return fg.atom_str(encoding="ascii")
    elif config["type"] == "rss":
        return fg.rss_str(encoding="ascii")


def process(config, path):
    generator = config["generator"]

    if not generator:
        return

    result = generator.generate(config, path)

    if result == None:
        return

    if config["brackets"]:
        result["title"] = "[%s] %s" % (generator.info["name"],
                                       result["title"])

    if config["type"] == "atom" or config["type"] == "rss":
        return process_feed(result, config)
    else:
        return


def http(config, path, get):
    for generator in rssit.generators.all.all_generators:
        result = generator.http(config, path, get)

        if result == None:
            continue


def update():
    importlib.reload(rssit.generators.all)
    rssit.generators.all.update()
