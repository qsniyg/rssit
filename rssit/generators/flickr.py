# -*- coding: utf-8 -*-


import re
import rssit.util
import json
import ujson
import demjson
import datetime
import urllib.parse
from dateutil.tz import *


info = {
    "name": "Flickr",
    "codename": "flickr",
    "config": {
        "author_username": False
    }
}


def check(url):
    return re.match(r"^https?://(?:\w+\.)?flickr\.com/photos/(?P<user>[^/]*)", url) != None


def generate(config, webpath):
    match = re.match(r"^https?://(?:\w+\.)?flickr\.com/photos/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    url = config["href"]

    data = rssit.util.download(url)

    jsondatare = re.search(r"modelExport: *(?P<json>.*?), *\\n", str(data))
    if jsondatare == None:
        return None
    jsondata = jsondatare.group("json")
    jsondata = rssit.util.fix_surrogates(jsondata.encode('utf-8').decode('unicode-escape'))
    decoded = ujson.loads(jsondata)

    photostream = decoded["photostream-models"][0]

    username = photostream["owner"]["username"]

    if not config["author_username"]:
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
