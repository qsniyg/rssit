# -*- coding: utf-8 -*-


import re
import rssit.util
from dateutil.tz import *
import bs4
import html
from dateutil.parser import parse
import urllib.parse
import isodate
import sys


def get_url(url):
    base = "/qurl/" # for now

    good = False

    if url.startswith("xe:"):
        url = url[len("xe:"):]
        good = True

    if url.startswith("//"):
        url = url[len("//"):]

    url = re.sub(r"^[^/]*://", "", url)

    if "/xe/" in url:
        good = True

    if good:
        return base + url
    else:
        return None


def getauthor(url):
    return re.sub("(http.*://)?([^/]*)/.*", "\\2", url)


def parse_date(date):
    return rssit.util.localize_datetime(parse(date))


def get_selector(soup, selectors):
    tag = None

    for selector in selectors:
        tag = soup.select(selector)
        if tag and len(tag) > 0:
            break
        else:
            tag = None

    return tag


def get_date(myjson, soup):
    datetag = get_selector(soup, [
        "b.tl",
        "div.info > span:nth-of-type(1) > b",
    ])

    if not datetag:
        sys.stderr.write("no recognizable date\n")
        return

    date = None
    for date_tag in datetag:
        date = parse_date(date_tag.text)

    return date


def get_caption(myjson, soup):
    captiontag = get_selector(soup, [
        "p > b",
        ".rt_area .ngeb"
    ])

    if not captiontag:
        return

    return captiontag[0].text


def get_entry_url(myjson, soup):
    urltag = get_selector(soup, [
        "a.hx"
    ])

    return urllib.parse.urljoin(myjson["url"], urltag[0]["href"])


def generate_url(config, url):
    data = rssit.util.download(url)
    soup = bs4.BeautifulSoup(data, 'lxml')

    author = getauthor(url)

    myjson = {
        "title": author,
        "author": author,
        "url": url,
        "entries": []
    }

    articles = get_selector(soup, [
        "ol.bd_lst > li"
    ])

    if not articles:
        sys.stderr.write("no recognizable articles\n")
        return

    for article in articles:
        caption = get_caption(myjson, article)
        date = get_date(myjson, article)
        entry_url = get_entry_url(myjson, article)

        entry = {
            "caption": caption,
            "date": date,
            "url": entry_url,
            "author": author,
            "images": [],
            "videos": []
        }

        myjson["entries"].append(entry)

    return ("social", myjson)


def process(server, config, path):
    if path.startswith("/url/"):
        url = "http://" + re.sub(".*?/url/", "", config["fullpath"])
        return generate_url(config, url)
    elif path.startswith("/qurl/"):
        url = "http://" + re.sub(".*?/qurl/", "", config["fullpath"])
        config["quick"] = True
        return generate_url(config, url)


infos = [{
    "name": "xe",
    "display_name": "XE",

    "config": {},

    "get_url": get_url,
    "process": process
}]
