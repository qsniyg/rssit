# -*- coding: utf-8 -*-


import re
import urllib.request
import json
import demjson
import datetime
from dateutil.tz import *
from feedgen.feed import FeedGenerator


def convert_surrogate_pair(x, y):
    n = (((ord(x) - 0xd800 << 10) + (ord(y) - 0xdc00)) + 0x10000)
    s = "\\U%08x" % n
    return s.encode('utf-8').decode("unicode-escape")


def fix_surrogates(string):
    new_string = ""

    last_surrogate = False

    for i in range(len(string)):
        ch = string[i]
        cho = ord(ch)

        if last_surrogate:
            last_surrogate = False
            continue

        if (cho >= 0xd800 and cho <= 0xdbff) or (cho >= 0xdc00 and cho <= 0xdfff):
            new_string += convert_surrogate_pair(ch, string[i + 1])
            last_surrogate = True
        else:
            new_string += ch

    return new_string


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
    fg.link(href=config["url"], rel="alternate")

    url = config["url"]

    request = urllib.request.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')
    request.add_header('Pragma', 'no-cache')
    request.add_header('Cache-Control', 'max-age=0')
    request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')

    with urllib.request.urlopen(request) as response:
           data = response.read()

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
            caption = fix_surrogates(captionjs).replace("\n","<br />\n")
        else:
            caption = ""



        date = datetime.datetime.fromtimestamp(int(node["date"]), None).replace(tzinfo=tzlocal())

        fe = fg.add_entry()
        fe.id("https://www.instagram.com/p/%s/" % node["code"])
        fe.link(href="https://www.instagram.com/p/%s/" % node["code"], rel="alternate")
        fe.title(caption)
        fe.description(caption)
        fe.author(name=user)
        fe.published(date)

        content = "<p>%s</p>" % caption

        if "is_video" in node and (node["is_video"] == "true" or node["is_video"] == True):
            content += "<p><em>Click to watch video</em></p>"
            content += "<a href='%s/%s'><img src='%s'/></a>" % (
                webpath, node["code"],
                node["display_src"]
            )
        else:
            content += "<img src='%s'/>" % node["display_src"]

        fe.content(content)

    return fg


def http(config, path, get):
    id = re.sub(r'^.*/', '', path)

    url = "https://www.instagram.com/p/%s/" % id

    request = urllib.request.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')
    request.add_header('Pragma', 'no-cache')
    request.add_header('Cache-Control', 'max-age=0')
    request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')

    with urllib.request.urlopen(request) as response:
           data = response.read()

    match = re.search(r"\"og:video\".*?content=\"(?P<video>.*?)\"", str(data))

    get.send_response(301, "Moved")
    get.send_header("Location", match.group("video"))
    get.end_headers()
