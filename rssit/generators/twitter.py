# -*- coding: utf-8 -*-


import datetime
import re
import rssit.util
import bs4
import demjson
import tweepy
import pprint
from calendar import timegm
import xml.sax.saxutils

try:
    from rfc822 import parsedate
except ImportError:
    from email.utils import parsedate


info = {
    "name": "Twitter",
    "codename": "twitter",
    "config": {
        "author_username": False,
        "with_replies": True,
        "consumer_key": "",
        "consumer_secret": "",
        "access_token": "",
        "access_secret": ""
    }
}


auths = {}
user_infos = {}


def get_string(element):
    if type(element) is bs4.element.NavigableString:
        return str(element.string)
    else:
        string = ""

        for i in element.children:
            string += get_string(i)

        return string


def check(url):
    return re.match(r"^https?://(?:\w+\.)?twitter.com/(?P<user>[^/]*)", url) != None


def generate_html(user, config, path):
    match = re.match(r"^https?://(?:\w+\.)?twitter.com/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    if config["with_replies"] and not config["url"].endswith("/with_replies"):
        data = rssit.util.download(config["url"] + "/with_replies")

    soup = bs4.BeautifulSoup(data, 'lxml')

    author = "@" + user
    description = "%s's twitter" % author

    init_data = soup.select("#init-data")

    if len(init_data) > 0:
        init_data = init_data[0]

        if "value" in init_data.attrs:
            init_json = demjson.decode(init_data.attrs["value"])

            if not config["author_username"]:
                if len(init_json["profile_user"]["name"]) > 0:
                    author = init_json["profile_user"]["name"]

            if len(init_json["profile_user"]["description"]) > 0:
                description = init_json["profile_user"]["description"]

            if len(init_json["profile_user"]["screen_name"]) > 0:
                user = init_json["profile_user"]["screen_name"]

    feed = {
        "title": author,
        "description": description,
        "author": user,
        "social": True,
        "entries": []
    }

    for tweet in soup.find_all(attrs={"data-tweet-id": True}):
        timestamp = int(tweet.find_all(attrs={"data-time": True})[0]["data-time"])
        date = rssit.util.localize_datetime(datetime.datetime.fromtimestamp(timestamp, None))

        username = tweet["data-screen-name"]

        link = tweet["data-permalink-path"]

        caption = ""
        urls = []

        for text in tweet.select("p.tweet-text"):
            for i in text.children:
                if type(i) is bs4.element.NavigableString:
                    caption += str(i.string)
                else:
                    if i.name == "img":
                        caption += i["alt"]
                    elif i.name == "a":
                        if "data-expanded-url" in i.attrs:
                            a_url = i["data-expanded-url"]
                            caption += a_url
                            urls.append(a_url)
                        elif not "u-hidden" in i["class"]:
                            caption += get_string(i)

        image_holder = tweet.find_all(attrs={"data-image-url": True})

        if len(image_holder) > 0:
            images = []

            for image in image_holder:
                image_url = image["data-image-url"]
                images.append(image_url)
        else:
            images = None

        #for url in urls:
        #    headers = rssit.util.download(url, head=True)

        is_video_el = tweet.select(".AdaptiveMedia-video")
        if len(is_video_el) > 0:
            tweet_id = tweet["data-tweet-id"]
            video_url = "https://twitter.com/i/videos/%s" % tweet_id
            pmp = tweet.select(".PlayableMedia-player")[0]
            preview_url = re.search(r"background-image: *url.'(?P<url>.*?)'",
                                   pmp["style"]).group("url")

            videos = [{
                "image": preview_url,
                "video": video_url
            }]
        else:
            videos = None

        feed["entries"].append({
            "url": link,
            "caption": caption,
            "author": username,
            "date": date,
            "updated_date": date,
            "images": images,
            "videos": videos
        })

    return feed


def generate_api(user, config, path):
    auth_key = config["consumer_key"] + config["consumer_secret"] +\
               config["access_token"] + config["access_secret"]

    if auth_key in auths:
        api = auths[auth_key]["api"]
    else:
        auth = tweepy.OAuthHandler(config["consumer_key"], config["consumer_secret"])
        auth.set_access_token(config["access_token"], config["access_secret"])

        api = tweepy.API(auth)

        auths[auth_key] = {
            "auth": auth,
            "api": api
        }

    if not user in user_infos:
        user_infos[user] = api.get_user(id=user)

    user_info = user_infos[user]

    title = "@" + user_info.screen_name

    if not config["author_username"] and "name" in user_info.__dict__ and len(user_info.name) > 0:
        title = user_info.name

    if "description" in user_info.__dict__ and len(user_info.description) > 0:
        description = user_info.description
    else:
        description = "%s's twitter" % title

    feed = {
        "title": title,
        "description": description,
        "author": user_info.screen_name,
        "social": True,
        "entries": []
    }


    tl = api.user_timeline(id=user, count=config["count"])

    if not tl:
        return None

    for obj in tl:
        #caption = xml.sax.saxutils.unescape(re.sub(" *http[^ ]*t\.co/[^ ]*", "", obj.text))
        #caption = xml.sax.saxutils.unescape(obj.text)
        origcaption = obj.text.replace("\r", "\n")
        newcaption = origcaption

        if "entities" in obj.__dict__:
            if "urls" in obj.entities:
                for url in obj.entities["urls"]:
                    newcaption = newcaption.replace(url["url"], url["expanded_url"])

        caption = xml.sax.saxutils.unescape(re.sub(" *https?://t\.co/[^ ]*", "", newcaption))
        #caption = xml.sax.saxutils.unescape(newcaption)

        #date = obj.created_at.timestamp()
        date = rssit.util.localize_datetime(datetime.datetime.fromtimestamp(timegm(parsedate(obj._json["created_at"])), None))

        entrydict = {
            "url": "https://twitter.com/statuses/" + obj.id_str,
            "caption": caption,
            "date": date,
            "updated_date": date,
            "author": obj.author.screen_name,
            "images": [],
            "videos": []
        }

        #pprint.pprint(obj.__dict__)

        if "extended_entities" in obj.__dict__:
            for media in obj.__dict__["extended_entities"]["media"]:
                if media["type"] == "photo":
                    entrydict["images"].append(media["media_url"])
                elif media["type"] == "video" or media["type"] == "animated_gif":
                    videodict = {
                        "image": media["media_url"]
                    }

                    variants = media["video_info"]["variants"]

                    max_bitrate = -1
                    curr = None
                    for variant in variants:
                        if "bitrate" in variant and variant["bitrate"] > max_bitrate:
                            curr = variant

                    if not curr:
                        curr = variants[0]

                    videodict["video"] = curr["url"]
                    entrydict["videos"].append(videodict)

        feed["entries"].append(entrydict)

    return feed


def generate(config, path):
    match = re.match(r"^https?://(?:\w+\.)?twitter.com/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    if len(config["consumer_key"]) > 0:
        return generate_api(user, config, path)
    else:
        return generate_html(user, config, path)
