# -*- coding: utf-8 -*-


import re
import rssit.util
import ujson
import datetime
import sys
from dateutil.tz import *


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


def generate_user(config, user):
    url = "https://www.instagram.com/" + user

    data = rssit.util.download(url)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare == None:
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = ujson.decode(jsondata)

    decoded_user =  decoded["entry_data"]["ProfilePage"][0]["user"]

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
            newdl = rssit.util.download("http://www.instagram.com/p/" + node["code"] + "/?__a=1")
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

    return ("social", feed)


def generate_video(server, id):
    url = "https://www.instagram.com/p/%s/" % id

    data = rssit.util.download(url)

    match = re.search(r"\"og:video\".*?content=\"(?P<video>.*?)\"", str(data))

    server.send_response(301, "Moved")
    server.send_header("Location", match.group("video"))
    server.end_headers()

    return True


def process(server, config, path):
    if path.startswith("/u/"):
        return generate_user(config, path[len("/u/"):])

    if path.startswith("/v/"):
        return generate_video(server, path[len("/v/"):])

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
