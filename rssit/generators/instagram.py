# -*- coding: utf-8 -*-


import re
import urllib.request
import json
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


def generate(config):
    match = re.match(r"^https?://www\.instagram\.com/(?P<user>[^/]*)", config["url"])

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
    decoded = json.loads(jsondata)

    nodes = decoded["entry_data"]["ProfilePage"][0]["user"]["media"]["nodes"]
    for node in reversed(nodes):
        captionjs = node["caption"].encode('utf-8').decode('unicode-escape')
        caption = fix_surrogates(captionjs).replace("\n","<br />\n")
        date = datetime.datetime.fromtimestamp(int(node["date"]), None).replace(tzinfo=tzlocal())

        fe = fg.add_entry()
        fe.id("https://www.instagram.com/p/%s/" % node["code"])
        fe.link(href="https://www.instagram.com/p/%s/" % node["code"], rel="alternate")
        fe.title(caption)
        fe.description(caption)
        fe.author(name=user)
        fe.published(date)
        fe.content("<p>%s</p><img src='%s'/>" % (caption, node["display_src"]))

    return fg
