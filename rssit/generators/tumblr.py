# -*- coding: utf-8 -*-


import bs4
import ujson
import sys
import urllib.request
from dateutil.parser import parse
import re
import html
import pprint
import rssit.util


def get_url(config, url):
    match = re.match(r"^(https?://)?(?P<url>[^./]*.tumblr.com.*)", url)

    if match is None:
        match = re.match(r"^tumblr:/*(https?://)?(?P<url>.*)", url)

        if match is None:
            return None

    return "/url/" + match.group("url")


def generate_url(config, url):
    url = rssit.util.quote_url(url)

    data = rssit.util.download(url)
    #data = rssit.util.download("file:///tmp/tumblr.html")

    soup = bs4.BeautifulSoup(data, 'lxml')

    jsondata = soup.find(attrs={"type": "application/ld+json"}).text
    jsondecode = ujson.loads(jsondata)

    myjson = {
        "title": None,
        "author": None,
        "url": url,
        "config": {
            "generator": "tumblr"
        },
        "entries": []
    }

    urls = [None]

    if jsondecode["@type"] == "ItemList":
        urls = []
        for item in jsondecode["itemListElement"]:
            urls.append(rssit.util.quote_url(item["url"]))

    i = 0
    for url in urls:
        if url:
            sys.stderr.write("\r[%i/%i] Downloading %s... " %
                             (i+1, len(urls), url))
            i = i + 1
            data = rssit.util.download(url)
            soup = bs4.BeautifulSoup(data, 'lxml')
            jsondata = soup.find(attrs={"type": "application/ld+json"}).text
            jsondecode = ujson.loads(jsondata)
            sys.stderr.write("done\n")

        author = jsondecode["author"]
        myjson["title"] = author
        myjson["author"] = author

        date = parse(jsondecode["datePublished"])

        if "headline" not in jsondecode:
            title = "[" + re.search("/post/([0-9]*)", jsondecode["url"]).group(1) + "]"

            if "articleBody" in jsondecode:
                title += " " + jsondecode["articleBody"]
        else:
            title = jsondecode["headline"]
        album = "[" + str(date.year)[-2:] + str(date.month).zfill(2) + str(date.day).zfill(2) + "] " + title

        if "image" not in jsondecode:
            continue

        if "@list" in jsondecode["image"]:
            images = jsondecode["image"]["@list"]
        else:
            images = [jsondecode["image"]]

        myjson["entries"].append({
            "caption": title,
            "url": url,
            #"album": album,
            "date": date,
            "author": author,
            "images": images,
            "videos": []
        })

    return ("social", myjson)


def process(server, config, path):
    if path.startswith("/url/"):
        url = "http://" + path[len("/url/"):]
        return generate_url(config, url)

    return None


infos = [{
    "name": "tumblr",
    "display_name": "Tumblr",

    "config": {},

    "get_url": get_url,
    "process": process
}]
