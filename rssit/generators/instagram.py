# -*- coding: utf-8 -*-


import re
import rssit.util
import ujson
import datetime
import sys
import pprint
import math
import urllib.parse
from dateutil.tz import *


instagram_ua = "Instagram 10.26.0 (iPhone7,2; iOS 10_1_1; en_US; en-US; scale=2.00; gamut=normal; 750x1334) AppleWebKit/420+"

endpoint_getentries = "https://www.instagram.com/graphql/query/?query_id=17888483320059182&variables="


def get_url(config, url):
    match = re.match(r"^(https?://)?(?:\w+\.)?instagram\.com/(?P<user>[^/]*)", url)

    if match is None:
        return

    if config["prefer_uid"]:
        return "/uid/" + get_user_page(config, match.group("user"))["id"]

    return "/u/" + match.group("user")


def normalize_image(url):
    url = url.replace(".com/l/", ".com/")
    url = re.sub(r"(cdninstagram\.com/[^/]*/)s[0-9]*x[0-9]*/", "\\1", url)
    return url


def base_image(url):
    return re.sub(r"\?[^/]*$", "", url)


def get_node_info(config, code):
    url = "http://www.instagram.com/p/" + code + "/?__a=1"
    newdl = rssit.util.download(url, config=config)
    return ujson.decode(newdl)


def get_node_media(config, node, images, videos):
    image_src = None
    if "display_src" in node:
        image_src = node["display_src"]
    elif "display_url" in node:
        image_src = node["display_url"]
    else:
        #pprint.pprint(node)
        sys.stderr.write("No image!!\n")
    normalized = normalize_image(image_src)

    if "is_video" in node and (node["is_video"] == "true" or node["is_video"] == True):
        if "video_url" in node:
            videourl = node["video_url"]
        else:
            #videourl = rssit.util.get_local_url("/f/instagram/v/" + node["code"])
            return get_node_media(config, get_node_info(config, node["code"])["graphql"]["shortcode_media"], images, videos)

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
        ok = True
        for image in images:
            if base_image(image) == base_image(normalized):
                ok = False
                break

        if ok:
            images.append(normalized)


def get_app_headers(config):
    config = rssit.util.simple_copy(config)
    config["httpheader_User-Agent"] = instagram_ua
    config["httpheader_x-ig-capabilities"] = "36oD"
    config["httpheader_accept"] = "*/*"
    #config["httpheader_accept-encoding"] = "gzip, deflate, br"
    config["httpheader_accept-language"] = "en-US,en;q=0.8"
    return config


def do_app_request(config, endpoint):
    config = get_app_headers(config)
    data = rssit.util.download(endpoint, config=config, http_noextra=True)
    return ujson.decode(data)


def get_stories(config, userid):
    storiesurl = "https://i.instagram.com/api/v1/feed/user/" + userid + "/story/"
    return do_app_request(config, storiesurl)


def get_user_info(config, userid):
    return do_app_request(config, "https://i.instagram.com/api/v1/users/" + userid + "/info/")


def get_user_page(config, username):
    url = "https://www.instagram.com/" + username + "/"  # / to avoid redirect

    data = rssit.util.download(url, config=config)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare is None:
        sys.stderr.write("No sharedData!\n")
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = ujson.decode(jsondata)

    return decoded["entry_data"]["ProfilePage"][0]["user"]


def generate_nodes_from_uid(config, uid, *args, **kwargs):
    variables = {
        "id": uid,
        "first": 12
    }

    for arg in kwargs:
        if kwargs[arg] is not None:
            variables[arg] = kwargs[arg]

    jsondumped = ujson.dumps(variables)
    url = endpoint_getentries + urllib.parse.quote(jsondumped)
    config = get_app_headers(config)
    data = rssit.util.download(url, config=config, http_noextra=True)
    #jsondata = bytes(str(data), 'utf-8').decode('unicode-escape')
    #print(jsondata)
    decoded = ujson.decode(data)
    #pprint.pprint(decoded)
    return decoded


def normalize_node(node):
    node = rssit.util.simple_copy(node)
    if "caption" not in node:
        if (("edge_media_to_caption" in node) and
            ("edges" in node["edge_media_to_caption"]) and
            (len(node["edge_media_to_caption"]["edges"]) > 0)):
            firstedge = node["edge_media_to_caption"]["edges"][0]
            node["caption"] = firstedge["node"]["text"]

    if "date" not in node:
        if "taken_at_timestamp" in node:
            node["date"] = node["taken_at_timestamp"]

    if "code" not in node:
        if "shortcode" in node:
            node["code"] = node["shortcode"]

    return node


def get_entry_from_node(config, node, user):
    node = normalize_node(node)

    if "caption" in node:
        caption = node["caption"]
    else:
        caption = None

    date = datetime.datetime.fromtimestamp(int(node["date"]), None).replace(tzinfo=tzlocal())

    images = []
    videos = []

    get_node_media(config, node, images, videos)

    if "__typename" in node and node["__typename"] == "GraphSidecar":
        newnodes = get_node_info(config, node["code"])

        if "edge_sidecar_to_children" not in newnodes["graphql"]["shortcode_media"]:
            sys.stderr.write("No 'edge_sidecar_to_children' property in " + sidecar_url + "\n")
        else:
            for newnode in newnodes["graphql"]["shortcode_media"]["edge_sidecar_to_children"]["edges"]:
                get_node_media(config, newnode["node"], images, videos)

    return {
        "url": "https://www.instagram.com/p/%s/" % node["code"],
        "caption": caption,
        "author": user,
        "date": date,
        "images": images,
        "videos": videos
    }


def get_story_entries(config, uid, username):
    storiesjson = get_stories(config, uid)

    if "reel" not in storiesjson or not storiesjson["reel"]:
        storiesjson["reel"] = {"items": []}

    if "post_live_item" not in storiesjson or not storiesjson["post_live_item"]:
        storiesjson["post_live_item"] = {"broadcasts": []}
        #return ("social", feed)

    #print(storiesjson)
    entries = []

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

        entries.append({
            "url": "http://guid.instagram.com/" + item["id"],#url,
            "caption": caption,
            "author": username,
            "date": date,
            "images": images,
            "videos": videos
        })

    for item in storiesjson["post_live_item"]["broadcasts"]:
        date = datetime.datetime.fromtimestamp(int(item["published_time"]), None).replace(tzinfo=tzlocal())

        entries.append({
            "url": "http://guid.instagram.com/" + item["media_id"],
            "caption": "[LIVE REPLAY]",
            "author": username,
            "date": date,
            "images": [],
            "videos": [{
                "image": item["cover_frame_url"],
                "video": rssit.util.get_local_url("/f/instagram/livereplay/" + item["media_id"])
            }]
        })

    return entries


def get_author(config, userinfo):
    author = "@" + userinfo["username"]

    if not config["author_username"]:
        if "full_name" in userinfo and type(userinfo["full_name"]) == str and len(userinfo["full_name"]) > 0:
            author = userinfo["full_name"]

    return author


def get_feed(config, userinfo):
    username = userinfo["username"]

    return {
        "title": get_author(config, userinfo),
        "description": "%s's instagram" % username,
        "url": "https://www.instagram.com/" + username + "/",
        "author": username,
        "entries": []
    }


def generate_uid(config, uid):
    userinfo = get_user_info(config, uid)
    feed = get_feed(config, userinfo["user"])

    username = userinfo["user"]["username"]
    mediacount = userinfo["user"]["media_count"]

    count = config["count"]
    times = 1
    if config["count"] == -1:
        maxcount = 500
        if mediacount <= maxcount:
            count = mediacount
            times = 1
        else:
            count = maxcount
            times = mediacount / maxcount

    i = 0
    after_cursor = None
    while i < times:
        if times > 1:
            sys.stderr.write("\rLoading media (%i/%i)... " % (i, math.ceil(times)))
        nodes = generate_nodes_from_uid(config, uid, first=count, after=after_cursor)
        edges = nodes["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
        pageinfo = nodes["data"]["user"]["edge_owner_to_timeline_media"]["page_info"]
        after_cursor = pageinfo["end_cursor"]

        for node in edges:
            node = node["node"]
            feed["entries"].append(get_entry_from_node(config, node, username))

        i += 1

    if times > 1:
        sys.stderr.write("\rLoading media... done       \n")

    story_entries = get_story_entries(config, uid, username)
    for entry in story_entries:
        feed["entries"].append(entry)

    return ("social", feed)


def generate_user(config, user):
    """url = "https://www.instagram.com/" + user + "/"  # / to avoid redirect

    data = rssit.util.download(url, config=config)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare is None:
        sys.stderr.write("No sharedData!\n")
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = ujson.decode(jsondata)

    decoded_user = decoded["entry_data"]["ProfilePage"][0]["user"]"""
    decoded_user = get_user_page(config, user)
    if config["force_api"]:
        return generate_uid(config, str(decoded_user["id"]))

    feed = get_feed(config, decoded_user)

    nodes = decoded_user["media"]["nodes"]
    for node in reversed(nodes):
        feed["entries"].append(get_entry_from_node(config, node, user))
        continue

    story_entries = get_story_entries(config, decoded_user["id"], user)
    for entry in story_entries:
        feed["entries"].append(entry)

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

    if path.startswith("/uid/"):
        return generate_uid(config, path[len("/uid/"):])

    return None


infos = [{
    "name": "instagram",
    "display_name": "Instagram",

    "config": {
        "author_username": {
            "name": "Author = Username",
            "description": "Set the author's name to be their username",
            "value": False
        },

        "prefer_uid": {
            "name": "Prefer user ID",
            "description": "Prefer user IDs over usernames",
            "value": True
        },

        "force_api": {
            "name": "Forces API",
            "description": "Forces the usage of the API",
            "value": False
        }
    },

    "get_url": get_url,
    "process": process
}]
