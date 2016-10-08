# -*- coding: utf-8 -*-


import re
import rssit.util
import ujson
import datetime
from dateutil.tz import *


def get_url(url):
    match = re.match(r"^https?://(?:\w+\.)?instagram\.com/(?P<user>[^/]*)", url)

    if match == None:
        return

    return "/u/" + match.group("user")


def generate_user(config, user):
    url = "https://www.instagram.com/" + user

    data = rssit.util.download(url)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare == None:
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = ujson.decode(jsondata)

    decoded_user =  decoded["entry_data"]["ProfilePage"][0]["user"]

    author = "@" + user

    if not config["author_username"]:
        if "full_name" in decoded_user and type(decoded_user["full_name"]) == str and len(decoded_user["full_name"]) > 0:
            decoded_user["full_name"]

    feed = {
        "title": author,
        "description": "%s's instagram" % user,
        "url": url,
        "author": user,
        "entries": []
    }

    nodes = decoded_user["media"]["nodes"]
    for node in reversed(nodes):
        if "caption" in node:
            caption = node["caption"]
        else:
            caption = None

        date = datetime.datetime.fromtimestamp(int(node["date"]), None).replace(tzinfo=tzlocal())

        images = None
        videos = None

        if "is_video" in node and (node["is_video"] == "true" or node["is_video"] == True):
            videos = [{
                "image": node["display_src"],
                "video": rssit.util.get_local_url("/f/instagram/v/" + node["code"])
            }]
        else:
            images = [node["display_src"]]

        feed["entries"].append({
            "url": "https://www.instagram.com/p/%s/" % node["code"],
            "caption": caption,
            "author": user,
            "date": date,
            "images": images,
            "videos": videos
        })

    return ("social", feed)


def generate_video(server, id):
    url = "https://www.instagram.com/p/%s/" % id

    data = rssit.util.download(url)

    match = re.search(r"\"og:video\".*?content=\"(?P<video>.*?)\"", str(data))

    server.send_response(301, "Moved")
    server.send_header("Location", match.group("video"))
    server.end_headers()

    return True


def process(server, config, path):
    if path.startswith("/u/"):
        return generate_user(config, path[len("/u/"):])

    if path.startswith("/v/"):
        return generate_video(server, path[len("/v/"):])

    return None


infos = [{
    "name": "instagram",
    "display_name": "Instagram",

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
