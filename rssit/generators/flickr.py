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
    match = re.match(r"^https?://(?:\w+\.)?flickr\.com/photos/(?P<user>[^/]*)/*", url)

    if match == None:
        return None

    data = rssit.util.download(url)
    decoded = get_modelExport(data)

    return "/p/" + decoded["photostream-models"][0]["owner"]["id"]


def generate(config, webpath):
    match = re.match(r"^https?://(?:\w+\.)?flickr\.com/photos/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    url = config["href"]

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

        images = [urllib.parse.urljoin(config["url"], photo["sizes"]["o"]["url"])]

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

    "get_url": get_url
}]
