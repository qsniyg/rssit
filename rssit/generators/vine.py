# -*- coding: utf-8 -*-


import datetime
import re
import rssit.util
import bs4


def get_url(url):
    match = re.match(r"^(https?://)?(?:\w+\.)?vine.co/.*", url)

    if match == None:
        return

    data = str(rssit.util.download(url))

    match = re.search("android-app:[^\"]*\/(?P<userid>[0-9]*)", data)
    if match == None:
        return

    userid = match.group("userid")

    return "/u/" + userid


def generate_user(config, user):
    url = "https://vine.co/u/" + user

    data = rssit.util.download(url)

    soup = bs4.BeautifulSoup(data, 'lxml')

    author_tag = soup.find(attrs={"property": "og:title"})
    if author_tag:
        author = re.match(r"^(?P<user>.*)'s Profile$", author_tag["content"]).group("user")

        if user == 'u':
            user = author
    else:
        author = user

    description_tag = soup.find(attrs={"property": "og:description"})

    if description_tag and len(description_tag["content"]) > 0:
        description = description_tag["content"]
    else:
        description = "%s's vine" % author

    feed = {
        "title": author,
        "author": user,
        "url": url,
        "description": description,
        "social": True,
        "entries": []
    }

    for post in soup.find_all(class_="post"):
        timestamp = re.search(r"(?P<date>[0-9][^ ]*)",
                              post.find(string=re.compile("Uploaded at"))).group("date")
        date = rssit.util.localize_datetime(datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S"))

        username = post.find("span").string

        link = post.select("h2 > a")[0]["href"]

        video = post.find("video")["src"]

        descriptiontag = post.find(class_="description")
        if descriptiontag:
            text = descriptiontag.string
        else:
            text = ""

        feed["entries"].append({
            "url": link,
            "caption": text,
            "author": username,
            "date": date,
            "images": None,
            "videos": [{
                "image": None,
                "video": video
            }]
        })

    return feed


def process(server, config, path):
    if path.startswith("/u/"):
        return ("social", generate_user(config, path[len("/u/"):]))

    return None


infos = [{
    "name": "vine",
    "display_name": "Vine",

    "config": {},

    "get_url": get_url,
    "process": process
}]
