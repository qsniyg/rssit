# -*- coding: utf-8 -*-


import re
import rssit.util
import json
import demjson
import datetime
from dateutil.tz import *


info = {
    "name": "Instagram",
    "codename": "instagram",
    "config": {
        "author_username": False
    }
}


def check(url):
    return re.match(r"^https?://(?:\w+\.)?instagram\.com/(?P<user>[^/]*)", url) != None


def generate(config, webpath):
    match = re.match(r"^https?://(?:\w+\.)?instagram\.com/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    url = config["url"]

    data = rssit.util.download(url)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare == None:
        return None
    jsondata = jsondatare.group("json")
    #decoded = json.loads(jsondata)
    decoded = demjson.decode(jsondata)

    decoded_user =  decoded["entry_data"]["ProfilePage"][0]["user"]

    author = "@" + user

    if not config["author_username"]:
        if len(decoded_user["full_name"]) > 0:
            author = decoded_user["full_name"]

    feed = {
        "title": author,
        "description": "%s's instagram" % user,
        "entries": []
    }

    nodes = decoded_user["media"]["nodes"]
    for node in reversed(nodes):
        if "caption" in node:
            captionjs = node["caption"].encode('utf-8').decode('unicode-escape')
            caption = rssit.util.fix_surrogates(captionjs)
        else:
            caption = "(n/a)"

        title = caption.replace("\n", " ")

        date = datetime.datetime.fromtimestamp(int(node["date"]), None).replace(tzinfo=tzlocal())

        content = "<p>%s</p>" % (caption.replace("\n", "<br />\n"))

        if "is_video" in node and (node["is_video"] == "true" or node["is_video"] == True):
            content += "<p><em>Click to watch video</em></p>"
            content += "<a href='%s/%s'><img src='%s'/></a>" % (
                webpath, node["code"],
                node["display_src"]
            )
        else:
            content += "<img src='%s'/>" % node["display_src"]

        feed["entries"].append({
            "url": "https://www.instagram.com/p/%s/" % node["code"],
            "title": title,
            "author": user,
            "date": date,
            "content": content
        })

    return feed


def http(config, path, get):
    id = re.sub(r'^.*/', '', path)

    url = "https://www.instagram.com/p/%s/" % id

    data = rssit.util.download(url)

    match = re.search(r"\"og:video\".*?content=\"(?P<video>.*?)\"", str(data))

    get.send_response(301, "Moved")
    get.send_header("Location", match.group("video"))
    get.end_headers()
