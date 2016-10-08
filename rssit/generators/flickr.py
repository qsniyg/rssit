# -*- coding: utf-8 -*-


import re
import rssit.util
import ujson
import datetime
import urllib.parse
from dateutil.tz import *


def get_modelExport(data):
    jsondatare = re.search(r"modelExport: *(?P<json>.*?), *\n", str(data))
    if jsondatare == None:
        return None

    jsondata = jsondatare.group("json")
    jsondata = rssit.util.fix_surrogates(jsondata)

    return ujson.loads(jsondata)


def get_url(url):
    match = re.match(r"^(https?://)?(?:\w+\.)?flickr\.com/photos/(?P<user>[^/]*)/*", url)

    if match == None:
        return None

    data = rssit.util.download(url)

    if not data:
        return None

    decoded = get_modelExport(data)

    if not decoded:
        return None

    return "/photos/" + decoded["photostream-models"][0]["owner"]["id"]


def generate_photos(config, user):
    url = "https://www.flickr.com/photos/" + user

    data = rssit.util.download(url)
    decoded = get_modelExport(data)

    photostream = decoded["photostream-models"][0]

    username = photostream["owner"]["username"]
    author = username

    if not config["author_username"] and "realname" in photostream["owner"]:
        if len(photostream["owner"]["realname"]) > 0:
            author = photostream["owner"]["realname"]

    feed = {
        "title": author,
        "description": "%s's flickr" % username,
        "url": url,
        "author": username,
        "social": True,
        "entries": []
    }

    photopage = photostream["photoPageList"]["_data"]
    for photo in photopage:
        if not photo:
            continue

        if "title" in photo:
            caption = photo["title"]
        else:
            caption = None

        date = datetime.datetime.fromtimestamp(int(photo["stats"]["datePosted"]), None).replace(tzinfo=tzlocal())

        images = [urllib.parse.urljoin(url, photo["sizes"]["o"]["url"])]

        feed["entries"].append({
            "url": "https://www.flickr.com/photos/%s/%s" % (
                user, photo["id"]
            ),
            "caption": caption,
            "author": username,
            "date": date,
            "images": images,
            "videos": None
        })

    return feed


def process(server, config, path):
    if path.startswith("/photos/"):
        return ("social", generate_photos(config, path[len("/photos/"):]))

infos = [{
    "name": "flickr",
    "display_name": "Flickr",

    "config": {
        "author_username": {
            "name": "Author = Username",
            "description": "Set the author's name to be their username",
            "value": False
        }
    },

    "get_url": get_url,
    "process": process
}]
