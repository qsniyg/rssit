# -*- coding: utf-8 -*-


import rssit.generators.all
import rssit.util
import importlib
import copy
import json
import subprocess
import threading

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

        basecontent = rssit.util.link_urls(caption.replace("\n", "<br />\n"))
        basetitle = caption.replace("\n", " ")

        if entry["author"] != result["author"]:
            content = "<p><em>%s</em></p><p>%s</p>" % (
                entry["author"],
                basecontent
            )

            title = "%s: %s" % (
                entry["author"],
                basetitle
            )
        else:
            content = "<p>%s</p>" % basecontent
            title = basetitle

        if entry["videos"]:
            for video in entry["videos"]:
                if "image" in video and video["image"]:
                    content += "<p><em>Click to watch video</em></p>"

                    content += "<a href='%s'><img src='%s'/></a>" % (
                        video["video"],
                        video["image"]
                    )
                else:
                    content += "<p><em><a href='%s'>Video</a></em></p>" % video["video"]

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


class waitthread(threading.Thread):
    def __init__(self, p, data):
        threading.Thread.__init__(self)
        self.p = p
        self.data = data

    def run(self):
        self.p.communicate(input=self.data)
        self.p.wait()


def copy_result(result):
    if type(result) == list:
        mylist = []

        for i in result:
            mylist.append(copy_result(i))

        return mylist
    elif type(result) == dict:
        mydict = {}

        for i in result:
            mydict[i] = copy_result(result[i])

        return mydict
    else:
        return result


def get_json(result, config):
    newresult = copy_result(result)
    newresult["config"] = copy.copy(config)
    newresult["config"]["generator"] = config["generator"].info["codename"]

    for entry in newresult["entries"]:
        entry["date"] = int(entry["date"].timestamp())

        if "updated_date" in entry:
            entry["updated_date"] = int(entry["updated_date"].timestamp())

    return json.dumps(newresult)


def social_download(result, config):
    myjson = get_json(result, config)

    if "download" in config and len(config["download"]) > 0:
        p = subprocess.Popen(config["download"], stdin=subprocess.PIPE,
                             stdout=None, stderr=None, close_fds=True,
                             shell=True)
        wt = waitthread(p, bytes(myjson, "utf-8"))
        wt.start()


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
        social_download(result, config)
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

        if "updated_date" in entry:
            fe.updated(entry["updated_date"])

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
        if not "http" in dir(generator):
            continue

        result = generator.http(config, path, get)

        if result == None:
            continue


def direct(config, generator_name):
    for generator in rssit.generators.all.all_generators:
        if generator.info["codename"] != generator_name:
            continue

        return generator.generate(config, None)


def update():
    importlib.reload(rssit.generators.all)
    rssit.generators.all.update()
