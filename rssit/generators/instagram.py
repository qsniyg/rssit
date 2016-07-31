# -*- coding: utf-8 -*-


import re
import rssit.util
import json
import demjson
import datetime
from dateutil.tz import *
from feedgen.feed import FeedGenerator


def check(url):
    return re.match(r"^https?://(?:\w+\.)?instagram\.com/(?P<user>[^/]*)", url) != None


def generate(config, webpath):
    match = re.match(r"^https?://(?:\w+\.)?instagram\.com/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    fg = FeedGenerator()
    fg.title("[Instagram] %s" % user)
    fg.description("[Instagram] %s" % user)
    fg.id(config["url"])
    fg.link(href=config["url"], rel="alternate")

    url = config["url"]

    data = rssit.util.download(url)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare == None:
        return None
    jsondata = jsondatare.group("json")
    #decoded = json.loads(jsondata)
    decoded = demjson.decode(jsondata)

    nodes = decoded["entry_data"]["ProfilePage"][0]["user"]["media"]["nodes"]
    for node in reversed(nodes):
        if "caption" in node:
            captionjs = node["caption"].encode('utf-8').decode('unicode-escape')
            caption = rssit.util.fix_surrogates(captionjs)
        else:
            caption = "(n/a)"

        title = caption.replace("\n", " ")

        date = datetime.datetime.fromtimestamp(int(node["date"]), None).replace(tzinfo=tzlocal())

        fe = fg.add_entry()
        fe.id("https://www.instagram.com/p/%s/" % node["code"])
        fe.link(href="https://www.instagram.com/p/%s/" % node["code"], rel="alternate")
        fe.title(title)
        fe.description(title)
        fe.author(name=user)
        fe.published(date)

        content = "<p>%s</p>" % (caption.replace("\n", "<br />\n"))

        if "is_video" in node and (node["is_video"] == "true" or node["is_video"] == True):
            content += "<p><em>Click to watch video</em></p>"
            content += "<a href='%s/%s'><img src='%s'/></a>" % (
                webpath, node["code"],
                node["display_src"]
            )
        else:
            content += "<img src='%s'/>" % node["display_src"]

        fe.content(content, type="html")

    return fg


def http(config, path, get):
    id = re.sub(r'^.*/', '', path)

    url = "https://www.instagram.com/p/%s/" % id

    data = rssit.util.download(url)

    match = re.search(r"\"og:video\".*?content=\"(?P<video>.*?)\"", str(data))

    get.send_response(301, "Moved")
    get.send_header("Location", match.group("video"))
    get.end_headers()
