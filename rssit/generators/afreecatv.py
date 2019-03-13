# -*- coding: utf-8 -*-

import time
import rssit.rest
import pprint
import re
import html
import random
import datetime
import dateutil.parser


def get_callback():
    num1 = str(int(random.random() * 10**21))
    num2 = str(int(random.random() * 10**13))
    return "jQuery" + num1 + "_" + num2


def get_time():
    utc = datetime.datetime.utcnow()
    return int(utc.timestamp() * 1000)


api = rssit.rest.API({
    "name": "afreecatv",
    "type": "json_callback",
    "cookiejar": "afreecatv",
    "method": "GET",
    "query": {
        "callback": rssit.rest.Arg("callback", 10),
        "szPlatformType": "main",
        "_": rssit.rest.Arg("time", 10)
    },
    "endpoints": {
        "favorite_feed": {
            "url": "http://live.afreecatv.com/afreeca/favorite_list_api.php",
            "query": {
                "nFixBroadCnt": 6,
                "szFrom": "webk",
                "szClub": "y",
                "lang": "ko_KR",
            }
        }
    }
})


def run_api(config, *args, **kwargs):
    newkwargs = rssit.util.simple_copy(kwargs)
    newkwargs["callback"] = get_callback()
    newkwargs["time"] = get_time()
    return api.run(config, *args, **newkwargs)


def generate_favorite_feed(server, config, path):
    response = run_api(config, "favorite_feed")

    config["is_index"] = True
    feed = {
        "title": "Favorite feed",
        "description": "Broadcasts from people you favorited",
        "url": "http://www.afreecatv.com/?hash=favorite",
        "author": "afreecatv",
        "entries": []
    }

    broadcasts = response["CHANNEL"]["ON_AIR_FAVORITE_BROAD"]
    for broadcast in broadcasts:
        date = dateutil.parser.parse(broadcast["broad_start"] + " +0900")
        url = "https://play.afreecatv.com/" + broadcast["user_id"] + "/" + broadcast["broad_no"]
        entry = {
            "caption": "[LIVE] " + html.unescape(broadcast["broad_title"]),
            "url": url,
            "date": date,
            "author": broadcast["user_id"],
            "images": [],
            "videos": []
        }
        feed["entries"].append(entry)

    return ("social", feed)


infos = [{
    "name": "afreecatv",
    "display_name": "AfreecaTV",

    "endpoints": {
        "favorite_feed": {
            "name": "Favorite Feed",
            "process": generate_favorite_feed
        },
    },

    "config": {

    }
}]
