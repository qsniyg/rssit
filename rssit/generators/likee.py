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
    "name": "likee",
    "type": "json",
    "endpoints": {
        "userpost": {
            "url": "https://likee.com/live/share/getUserPost",
            "query": {
                "u": rssit.rest.Arg("userId", 1),
                "currentUrl": rssit.rest.Arg("currentUrl", 2),
                "count": rssit.rest.Arg("count", 3),
                "last_postid": rssit.rest.Arg("lastPostId", 4)
            }
        },
        "uservideo": {
            "url": "https://likee.com/official_website/VideoApi/getUserVideo",
            "method": "POST",
            "form": {
                "uid": rssit.rest.Arg("userId", 1),
                "count": rssit.rest.Arg("count", 2),
                "lastPostId": rssit.rest.Arg("lastPostId", 3)
            },
            "headers": {
                "origin": "https://likee.com",
                "referer": "https://likee.com",
                "content-type": "application/x-www-form-urlencoded"
            }
        }
    }
})

userinfo_by_username_cache = rssit.util.Cache("likee_userinfo_by_username", 48*60*60, 100)


def username_to_url(username):
    return "https://likee.com/@" + username.lower()


def fetch_userinfo_webpage(config, username):
    data = rssit.util.download(username_to_url(username), config=config)
    sdata = data.decode('utf-8')

    need_check_userinfo = False

    userinfore = re.search(r"<script>var\s+userinfo\s*=\s*(?P<json>{.*})\s*;", sdata)
    if userinfore is None:
        userinfore = re.search(r"<script>window\.data\s*=\s*(?P<json>{.*?})\s*;</script>", sdata)
        if userinfore is None:
            return None

    json = rssit.util.json_loads(userinfore.group("json"))

    if need_check_userinfo:
        return json["userinfo"]
    else:
        return json


def userinfo_by_username(config, username):
    userinfo = userinfo_by_username_cache.get(username)
    if not userinfo:
        userinfo = fetch_userinfo_webpage(config, username)
        userinfo_by_username_cache.add(username, userinfo)

    return userinfo


def username_to_uid(config, username):
    return userinfo_by_username(config, username)["uid"]


def normalize_video_page_url(url):
    return url.replace("/trending/@", "/@").lower()


def normalize_image_url(url):
    return re.sub(r"(/[0-9A-Za-z]+)_[12](\.[^/.]+)(?:[?#].*)?$", "\\1_4\\2", url)


def normalize_video_url(url):
    return re.sub(r"(/[0-9A-Za-z]+)_[0-9]+(\.[^/.]+)(?:[?#].*)?$", "\\1\\2", url)


def post_to_entry(config, username, obj):
    entry = {
        "caption": obj["description"],
        "url": obj["share_url"],
        "guid": normalize_video_page_url(obj["url"]),
        "author": username,
        "date": rssit.util.parse_date(obj["uploadDate"]),
        "images": [],
        "videos": [{
            "image": normalize_image_url(obj["thumbnailUrl"]),
            "video": normalize_video_url(obj["contentUrl"])
        }]
    }

    return entry


def video_to_entry(config, username, obj):
    shareurl = username_to_url(username) + "/video/" + obj["postId"]

    entry = {
        "caption": obj["msgText"],
        "url": shareurl,
        "guid": shareurl,
        "author": username,
        # not utcfromtimestamp
        "date": rssit.util.localize_datetime(datetime.datetime.fromtimestamp(int(obj["postTime"]))),
        "images": [],
        "videos": [{
            "image": normalize_image_url(obj["coverUrl"]),
            "video": normalize_video_url(obj["videoUrl"])
        }]
    }

    return entry


def generate_user(server, config, path):
    username = path.lower()

    userinfo = userinfo_by_username(config, username)
    uid = userinfo["uid"]
    username_url = username_to_url(username)

    count = config["page_count"]
    if "count" in config and config["count"] > 1:
        count = config["count"]

    feed = {
        "title": userinfo["nick_name"],
        "author": username,
        "description": userinfo["bio"],
        "url": username_url,
        "config": {
            "generator": "likee"
        },
        "entries": []
    }

    dp_link = userinfo["bigUrl"]
    dp_guid = re.sub(r"(?:.*/)?([^/.]+)(?:\.[^/.]+)(?:[?#].*)?$", "\\1", os.path.basename(dp_link))
    feed["entries"].append({
        "caption": "[DP] " + dp_guid,
        "author": username,
        "url": dp_link,
        "date": rssit.util.parse_date(-1),
        "images": [dp_link],
        "videos": []
    })

    def get_entries(maxid):
        apioptions = {
            "userId": uid,
            "currentUrl": username_url,
            "count": count
        }

        if maxid:
            apioptions["lastPostId"] = maxid

        if False:
            response = api.run(config, "userpost", **apioptions)

            postlist = response["post_list"]
            has_next_page = len(postlist) > 0
            if has_next_page:
                nextid = response["post_list"][-1]["post_id"]
            else:
                nextid = None
            return (postlist, nextid, has_next_page)
        else:
            if "lastPostId" not in apioptions:
                apioptions["lastPostId"] = ""

            response = api.run(config, "uservideo", **apioptions)["data"]

            postlist = response["videoList"]
            has_next_page = len(postlist) > 0
            if has_next_page:
                nextid = response["videoList"][-1]["postId"]
            else:
                nextid = None
            return (postlist, nextid, has_next_page)

    posts = rssit.util.paginate(config, None, get_entries)

    for post in posts:
        if False:
            feed["entries"].append(post_to_entry(config, username, post))
        else:
            feed["entries"].append(video_to_entry(config, username, post))

    return ("social", feed)


infos = [{
    "name": "likee",
    "display_name": "Likee",

    "endpoints": {
        "user": {
            "name": "User",
            "process": generate_user
        }
    },

    "config": {
        "page_count": {
            "name": "Page count",
            "description": "Elements to query per page",
            "value": 30
        }
    }
}]
