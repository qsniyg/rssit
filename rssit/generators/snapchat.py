# -*- coding: utf-8 -*-

import rssit.util
import rssit.rest
import pprint
import json
import os.path
import re
import urllib.parse
import datetime

api = rssit.rest.API({
    "name": "snapchat",
    "type": "json",
    "endpoints": {
        "userstory": {
            "url": "https://search.snapchat.com/lookupStory",
            "query": {
                "id": rssit.rest.Arg("username", 1)
            },
            "headers": {
                "origin": "https://www.snapchat.com",
                "referer": "https://www.snapchat.com/"
            }
        }
    }
})


def snap_to_entry(username, snap):
    images = []
    videos = []

    mediaurl = snap["snapUrls"]["mediaUrl"]

    if ".mp4" in mediaurl:
        videos.append({
            "image": mediaurl.replace("/media.mp4", "/preview.jpg"),
            "video": mediaurl
        })
    else:
        images.append(mediaurl)

    return {
        "caption": None,
        "url": "https://guid.snapchat.com/" + snap["snapId"],
        "guid": snap["snapId"],
        "author": username,
        "date": rssit.util.localize_datetime(datetime.datetime.fromtimestamp(snap["timestampInSec"])),
        "images": images,
        "videos": videos
    }


def generate_user(server, config, path):
    username = path # not .lower(), usernames are case sensitive

    response = api.run(config, "userstory", username=username)

    feed = {
        "title": response["storyTitle"],
        "author": response["userName"],
        "description": None,
        "url": "https://www.snapchat.com/add/" + username,
        "config": {
            "generator": "snapchat"
        },
        "entries": []
    }

    snaplist = response["snapList"]
    for snap in snaplist:
        feed["entries"].append(snap_to_entry(username, snap))

    return ("social", feed)


infos = [{
    "name": "snapchat",
    "display_name": "Snapchat",

    "endpoints": {
        "user": {
            "name": "User",
            "process": generate_user
        }
    },

    "config": {}
}]
