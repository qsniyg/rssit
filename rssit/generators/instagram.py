# -*- coding: utf-8 -*-


import re
import rssit.util
import ujson
import datetime
import sys
import pprint
from dateutil.tz import *


instagram_ua = "Instagram 10.26.0 (iPhone7,2; iOS 10_1_1; en_US; en-US; scale=2.00; gamut=normal; 750x1334) AppleWebKit/420+"


def get_url(url):
    match = re.match(r"^(https?://)?(?:\w+\.)?instagram\.com/(?P<user>[^/]*)", url)

    if match == None:
        return

    return "/u/" + match.group("user")


def normalize_image(url):
    url = url.replace(".com/l/", ".com/")
    url = re.sub(r"(cdninstagram\.com/[^/]*/)s[0-9]*x[0-9]*/", "\\1", url)
    return url


def get_node_media(node, images, videos):
    image_src = None
    if "display_src" in node:
        image_src = node["display_src"]
    elif "display_url" in node:
        image_src = node["display_url"]
    else:
        sys.stderr.write("No image!!\n")
    normalized = normalize_image(image_src)

    if "is_video" in node and (node["is_video"] == "true" or node["is_video"] == True):
        if "video_url" in node:
            videourl = node["video_url"]
        else:
            videourl = rssit.util.get_local_url("/f/instagram/v/" + node["code"])

        found = False
        for video in videos:
            if video["video"] == videourl:
                found = True
                break

        if not found:
            videos.append({
                "image": normalized,
                "video": videourl
            })
    else:
        if normalized not in images:
            images.append(normalized)


def get_app_headers(config):
    config["httpheader_User-Agent"] = instagram_ua
    config["httpheader_x-ig-capabilities"] = "36oD"
    config["httpheader_accept"] = "*/*"
    #config["httpheader_accept-encoding"] = "gzip, deflate, br"
    config["httpheader_accept-language"] = "en-US,en;q=0.8"
    return config


def get_stories(config, userid):
    storiesurl = "https://i.instagram.com/api/v1/feed/user/" + userid + "/story/"
    #config["httpheader_User-Agent"] = instagram_ua
    #config["httpheader_x-ig-capabilities"] = "36oD"
    #config["httpheader_accept"] = "*/*"
    ##config["httpheader_accept-encoding"] = "gzip, deflate, br"
    #config["httpheader_accept-language"] = "en-US,en;q=0.8"
    config = get_app_headers(config)
    stories_data = rssit.util.download(storiesurl, config=config, http_noextra=True)
    storiesjson = ujson.decode(stories_data)
    return storiesjson


def generate_user(config, user):
    url = "https://www.instagram.com/" + user + "/"  # / to avoid redirect

    data = rssit.util.download(url, config=config)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare == None:
        sys.stderr.write("No sharedData!\n")
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = ujson.decode(jsondata)

    decoded_user = decoded["entry_data"]["ProfilePage"][0]["user"]

    author = "@" + user

    if not config["author_username"]:
        if "full_name" in decoded_user and type(decoded_user["full_name"]) == str and len(decoded_user["full_name"]) > 0:
            author = decoded_user["full_name"]

    feed = {
        "title": author,
        "description": "%s's instagram" % user,
        "url": url,
        "author": user,
        "entries": []
    }

    nodes = decoded_user["media"]["nodes"]
    for node in reversed(nodes):
        if "caption" in node:
            caption = node["caption"]
        else:
            caption = None

        date = datetime.datetime.fromtimestamp(int(node["date"]), None).replace(tzinfo=tzlocal())

        images = []
        videos = []

        get_node_media(node, images, videos)

        #if "is_video" in node and (node["is_video"] == "true" or node["is_video"] == True):
        #    videos = [{
        #        "image": normalize_image(node["display_src"]),
        #        "video": rssit.util.get_local_url("/f/instagram/v/" + node["code"])
        #    }]
        #else:
        #    images = [normalize_image(node["display_src"])]

        if "__typename" in node and node["__typename"] == "GraphSidecar":
            sidecar_url = "http://www.instagram.com/p/" + node["code"] + "/?__a=1"
            newdl = rssit.util.download("http://www.instagram.com/p/" + node["code"] + "/?__a=1", config=config)
            newnodes = ujson.decode(newdl)

            if "edge_sidecar_to_children" not in newnodes["graphql"]["shortcode_media"]:
                sys.stderr.write("No 'edge_sidecar_to_children' property in " + sidecar_url + "\n")
            else:
                for newnode in newnodes["graphql"]["shortcode_media"]["edge_sidecar_to_children"]["edges"]:
                    get_node_media(newnode["node"], images, videos)

        feed["entries"].append({
            "url": "https://www.instagram.com/p/%s/" % node["code"],
            "caption": caption,
            "author": user,
            "date": date,
            "images": images,
            "videos": videos
        })

    """storiesurl = "https://i.instagram.com/api/v1/feed/user/" + decoded_user["id"] + "/story/"
    config["httpheader_User-Agent"] = instagram_ua
    config["httpheader_x-ig-capabilities"] = "36oD"
    config["httpheader_accept"] = "*/*"
    #config["httpheader_accept-encoding"] = "gzip, deflate, br"
    config["httpheader_accept-language"] = "en-US,en;q=0.8"
    stories_data = rssit.util.download(storiesurl, config=config, http_noextra=True)
    #print(stories_data)

    storiesjson = ujson.decode(stories_data)"""
    storiesjson = get_stories(config, decoded_user["id"])

    if "reel" not in storiesjson or not storiesjson["reel"]:
        storiesjson["reel"] = {"items": []}

    if "post_live_item" not in storiesjson or not storiesjson["post_live_item"]:
        storiesjson["post_live_item"] = {"broadcasts": []}
        #return ("social", feed)

    #print(storiesjson)

    for item in storiesjson["reel"]["items"]:
        #print(item)
        image = item["image_versions2"]["candidates"][0]["url"]
        url = image
        images = [image]
        videos = []
        if "video_versions" in item and item["video_versions"]:
            videos = [{
                "image": image,
                "video": item["video_versions"][0]["url"]
            }]
            url = videos[0]["video"]
            images = []

        caption = "[STORY]"

        if "caption" in item and item["caption"] and "text" in item["caption"]:
            caption = "[STORY] " + str(item["caption"]["text"])

        date = datetime.datetime.fromtimestamp(int(item["taken_at"]), None).replace(tzinfo=tzlocal())

        feed["entries"].append({
            "url": "http://guid.instagram.com/" + item["id"],#url,
            "caption": caption,
            "author": user,
            "date": date,
            "images": images,
            "videos": videos
        })

    for item in storiesjson["post_live_item"]["broadcasts"]:
        date = datetime.datetime.fromtimestamp(int(item["published_time"]), None).replace(tzinfo=tzlocal())

        feed["entries"].append({
            "url": "http://guid.instagram.com/" + item["media_id"],
            "caption": "[LIVE REPLAY]",
            "author": user,
            "date": date,
            "images": [],
            "videos": [{
                "image": item["cover_frame_url"],
                "video": rssit.util.get_local_url("/f/instagram/livereplay/" + item["media_id"])
            }]
        })
        #pprint.pprint(item)

    """reelsurl = "https://i.instagram.com/api/v1/feed/reels_tray/"
    reels_data = rssit.util.download(reelsurl, config=config, http_noextra=True)

    reelsjson = ujson.decode(reels_data)"""

    return ("social", feed)


def generate_video(config, server, id):
    url = "https://www.instagram.com/p/%s/" % id

    data = rssit.util.download(url, config=config)

    match = re.search(r"\"og:video\".*?content=\"(?P<video>.*?)\"", str(data))

    server.send_response(301, "Moved")
    server.send_header("Location", match.group("video"))
    server.end_headers()

    return True


def generate_livereplay(config, server, id):
    reelsurl = "https://i.instagram.com/api/v1/feed/reels_tray/"
    config = get_app_headers(config)
    reels_data = rssit.util.download(reelsurl, config=config, http_noextra=True)

    reelsjson = ujson.decode(reels_data)

    for live in reelsjson["post_live"]["post_live_items"]:
        for broadcast in live["broadcasts"]:
            if id == broadcast["media_id"]:
                server.send_response(200, "OK")
                server.send_header("Content-type", "application/xml")
                server.end_headers()
                server.wfile.write(broadcast["dash_manifest"].encode('utf-8'))
                return True

    sys.stderr.write("Unable to find media id %s\n" % id)
    return None


def process(server, config, path):
    if path.startswith("/u/"):
        return generate_user(config, path[len("/u/"):])

    if path.startswith("/v/"):
        return generate_video(config, server, path[len("/v/"):])

    if path.startswith("/livereplay/"):
        return generate_livereplay(config, server, path[len("/livereplay/"):])

    return None


infos = [{
    "name": "instagram",
    "display_name": "Instagram",

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
