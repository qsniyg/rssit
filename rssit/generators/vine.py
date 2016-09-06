# -*- coding: utf-8 -*-


import datetime
import re
import rssit.util
import bs4
import demjson


info = {
    "name": "Vine",
    "codename": "vine",
    "config": {}
}


def check(url):
    return re.match(r"^https?://(?:\w+\.)?vine.co/(?P<user>[^/]*)", url) != None


def generate(config, path):
    match = re.match(r"^https?://(?:\w+\.)?vine.co/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    data = rssit.util.download(config["url"])

    soup = bs4.BeautifulSoup(data, 'lxml')

    author_tag = soup.find(attrs={"property": "og:title"})
    if author_tag:
        author = re.match(r"^(?P<user>.*)'s Profile$", author_tag["content"]).group("user")
    else:
        author = user

    description_tag = soup.find(attrs={"property": "og:description"})

    if description_tag:
        description = description_tag["content"]
    else:
        description = "%s's vine" % author

    feed = {
        "title": author,
        "description": description,
        "entries": []
    }

    for post in soup.find_all(class_="post"):
        timestamp = re.search(r"(?P<date>[0-9][^ ]*)",
                              post.find(string=re.compile("Uploaded at"))).group("date")
        date = rssit.util.localize_datetime(datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S"))

        username = post.find("span").string

        link = post.select("h2 > a")[0]["href"]

        video = post.find("video")["src"]

        text = post.find(class_="description").string
        content = "<p>" + text + "</p><p><a href='%s'>Video</a></p>" % video

        feed["entries"].append({
            "url": link,
            "title": text,
            "author": username,
            "date": date,
            "content": content
        })

    return feed
