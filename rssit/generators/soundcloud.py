# -*- coding: utf-8 -*-


import re
import rssit.util
from dateutil.tz import *
import bs4
import html
from dateutil.parser import parse
import urllib.parse
import isodate


def get_url(config, url):
    match = re.match(r"^(https?://)?(?:\w+\.)?soundcloud\.com/(?P<user>[^/]*)", url)

    if match == None:
        return

    return "/u/" + match.group("user")


def generate_user(config, user):
    url = "https://www.soundcloud.com/" + user

    data = rssit.util.download(url)

    soup = bs4.BeautifulSoup(data, 'lxml')

    author = html.unescape(soup.find("meta", attrs={"property": "og:title"})["content"])

    if config["author_username"]:
        author = user

    description = html.unescape(soup.find("p", attrs={"itemprop": "description"}).text).strip()
    if len(description) <= 0:
        description = "%s's soundcloud" % user

    feed = {
        "title": author,
        "description": description,
        "url": url,
        "author": user,
        "entries": []
    }

    tracks = soup.findAll("article", attrs={"itemprop": "track"})
    for track in tracks:
        tracka = track.find("a", attrs={"itemprop": "url"})
        trackname = tracka.text
        trackurl = urllib.parse.urljoin(url, tracka["href"])
        date = parse(track.find("time").text)

        title = trackname
        duration_delta = isodate.parse_duration(track.find("meta", attrs={"itemprop": "duration"})["content"])
        duration_seconds = duration_delta.total_seconds()
        duration_text = "[%s:%s:%s]" % (
            str(int(duration_seconds / 3600)).zfill(2),
            str(int((duration_seconds % 3600) / 60)).zfill(2),
            str(int(duration_seconds % 60)).zfill(2)
        )

        content = "<p>%s <a href='%s'>%s</a> by <a href='%s'>%s</a></p>" % (
            duration_text,

            trackurl,
            trackname,

            url,
            author
        )

        feed["entries"].append({
            "url": trackurl,
            "title": title,
            "content": content,
            "author": user,
            "date": date,
        })

    return ("feed", feed)



def process(server, config, path):
    if path.startswith("/u/"):
        return generate_user(config, path[len("/u/"):])

    return None


infos = [{
    "name": "soundcloud",
    "display_name": "Soundcloud",

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
