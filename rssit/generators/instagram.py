# -*- coding: utf-8 -*-


import re
import rssit.util
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
    """url = url.replace(".com/l/", ".com/")
    url = re.sub(r"(cdninstagram\.com/[^/]*/)s[0-9]*x[0-9]*/", "\\1", url)
    url = re.sub(r"/sh[0-9]*\.[0-9]*/", "/", url)
    url = re.sub(r"/p[0-9]*x[0-9]*/", "/", url)
    url = re.sub(r"/e[0-9]*/", "/", url)
    url = url.replace("/fr/", "/")
    url = re.sub(r"(cdninstagram\.com/[^/]*/)s[0-9]*x[0-9]*/", "\\1", url)"""

    urlsplit = urllib.parse.urlsplit(url)
    urlstart = urlsplit.scheme + "://" + urlsplit.netloc + "/"

    pathsplit = urlsplit.path.split("/")

    for i in pathsplit:
        if re.match(r"^t[0-9]+\.[0-9]+-[0-9]+$", i):
            urlstart += i + "/"
        elif re.match(r"^[0-9_]*_[a-z]+\.[a-z0-9]+$", i):
            urlstart += i

    return urlstart
    #url = url.replace(r"(cdninstagram\.com/).*/t[0-9]+\.[0-9]+-[0-9]+/.*
    #return url


def base_image(url):
    return re.sub(r"\?[^/]*$", "", url)


def do_a1_request(config, endpoint, *args, **kwargs):
    url = "http://www.instagram.com/" + endpoint.strip("/") + "/?__a=1"
    if "extra" in kwargs and kwargs["extra"]:
        url += "&" + kwargs["extra"]
    newdl = rssit.util.download(url, config=config)
    return rssit.util.json_loads(newdl)


def get_node_info(config, code):
    return do_a1_request(config, "/p/" + code)
    #url = "http://www.instagram.com/p/" + code + "/?__a=1"
    #newdl = rssit.util.download(url, config=config)
    #return ujson.decode(newdl)


def get_node_media(config, node, images, videos):
    node = normalize_node(node)

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

    if node["type"] == "carousel":
        def carousel_has_nonimage_member(carousel):
            for i in carousel:
                if "display_url" not in normalize_node(i):
                    return True
            return False

        if "carousel_media" in node and not carousel_has_nonimage_member(node["carousel_media"]):
            for i in node["carousel_media"]:
                get_node_media(config, i, images, videos)
        else:
            newnodes = get_node_info(config, node["code"])
            get_node_media(config, newnodes["graphql"]["shortcode_media"], images, videos)

            #if "edge_sidecar_to_children" not in newnodes["graphql"]["shortcode_media"]:
            #    sys.stderr.write("No 'edge_sidecar_to_children' property in " + sidecar_url + "\n")
            #else:
            #    for newnode in newnodes["graphql"]["shortcode_media"]["edge_sidecar_to_children"]["edges"]:
            #        get_node_media(config, newnode["node"], images, videos)


def get_app_headers(config):
    config = rssit.util.simple_copy(config)
    config["httpheader_User-Agent"] = instagram_ua
    config["httpheader_x-ig-capabilities"] = "36oD"
    config["httpheader_accept"] = "*/*"
    #config["httpheader_accept-encoding"] = "gzip, deflate, br"
    config["httpheader_accept-language"] = "en-US,en;q=0.8"
    return config


def has_cookie(config):
    for key in config:
        if key.lower() == "httpheader_cookie" and config[key]:
            return True
    return False


def do_app_request(config, endpoint):
    if not has_cookie(config):
        return None

    config = get_app_headers(config)
    data = rssit.util.download(endpoint, config=config, http_noextra=True)
    return rssit.util.json_loads(data)


def get_stories(config, userid):
    storiesurl = "https://i.instagram.com/api/v1/feed/user/" + userid + "/story/"
    return do_app_request(config, storiesurl)


def get_user_info(config, userid):
    return do_app_request(config, "https://i.instagram.com/api/v1/users/" + userid + "/info/")


def get_user_info_by_username(config, username, *args, **kwargs):
    extra = None
    if "max_id" in kwargs and kwargs["max_id"]:
        extra = "max_id=" + str(kwargs["max_id"])
    return do_a1_request(config, username, extra=extra)["user"]


def get_user_media_by_username(config, username):
    return do_a1_request(config, username + "/media")["items"]


def get_user_page(config, username):
    url = "https://www.instagram.com/" + username + "/"  # / to avoid redirect

    data = rssit.util.download(url, config=config)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare is None:
        sys.stderr.write("No sharedData!\n")
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = rssit.util.json_loads(jsondata)

    return decoded["entry_data"]["ProfilePage"][0]["user"]


def generate_nodes_from_uid(config, uid, *args, **kwargs):
    variables = {
        "id": uid,
        "first": 12
    }

    for arg in kwargs:
        if kwargs[arg] is not None:
            variables[arg] = kwargs[arg]

    jsondumped = rssit.util.json_dumps(variables)
    url = endpoint_getentries + urllib.parse.quote(jsondumped)
    config = get_app_headers(config)
    data = rssit.util.download(url, config=config, http_noextra=True)
    #jsondata = bytes(str(data), 'utf-8').decode('unicode-escape')
    #print(jsondata)
    decoded = rssit.util.json_loads(data)
    #pprint.pprint(decoded)
    return decoded


def force_array(obj):
    if type(obj) == dict:
        a = []
        for i in obj:
            a.append(obj[i])
        return a
    return a


def get_largest_url(items):
    max_ = 0
    url = None
    for item in force_array(items):
        total = item["height"] + item["width"]
        if total > max_:
            max_ = total
            url = item["url"]
    return url


def normalize_node(node):
    node = rssit.util.simple_copy(node)
    if "caption" not in node:
        if (("edge_media_to_caption" in node) and
            ("edges" in node["edge_media_to_caption"]) and
            (len(node["edge_media_to_caption"]["edges"]) > 0)):
            firstedge = node["edge_media_to_caption"]["edges"][0]
            node["caption"] = firstedge["node"]["text"]

    if "caption" in node and type(node["caption"]) == dict:
        node["caption"] = node["caption"]["text"]

    if "date" not in node:
        if "taken_at_timestamp" in node:
            node["date"] = node["taken_at_timestamp"]
        elif "created_time" in node:
            node["date"] = int(node["created_time"])

    if "code" not in node:
        if "shortcode" in node:
            node["code"] = node["shortcode"]

    if "type" not in node:
        if "__typename" in node:
            if node["__typename"] == "GraphImage":
                node["type"] = "image"
            elif node["__typename"] == "GraphVideo":
                node["type"] = "video"
            elif node["__typename"] == "GraphSidecar":
                node["type"] = "carousel"

    if "is_video" not in node:
        node["is_video"] = node["type"] == "video"

    if "video_url" not in node:
        if "videos" in node:
            new_url = get_largest_url(node["videos"])
            if new_url:
                node["video_url"] = new_url
            """max_ = 0
            for video in node["videos"]:
                total = video["height"] + video["width"]
                if total > max_:
                    max_ = total
                    node["video_url"] = video["url"]"""

    if "display_url" not in node:
        if "images" in node:
            new_url = get_largest_url(node["images"])
            if new_url:
                node["display_url"] = new_url

    if node["type"] == "carousel" and "carousel_media" not in node:
        if "edge_sidecar_to_children" in node:
            node["carousel_media"] = []
            for newnode in node["edge_sidecar_to_children"]["edges"]:
                node["carousel_media"].append(newnode["node"])

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

    if "__typename" in node and node["__typename"] == "GraphSidecar" and False:
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

    if not storiesjson:
        sys.stderr.write("Warning: not logged in, so no stories\n")
        return []

    if "reel" not in storiesjson or not storiesjson["reel"]:
        storiesjson["reel"] = {"items": []}

    if "post_live_item" not in storiesjson or not storiesjson["post_live_item"]:
        storiesjson["post_live_item"] = {"broadcasts": []}
        #return ("social", feed)

    #print(storiesjson)
    entries = []

    for item in storiesjson["reel"]["items"]:
        #print(item)
        image = normalize_image(item["image_versions2"]["candidates"][0]["url"])
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

        extra = ""
        if "story_cta" in item and item["story_cta"]:
            links = []
            for cta in item["story_cta"]:
                for thing in cta:
                    if thing == "links":
                        for link in cta["links"]:
                            links.append(link["webUri"])
                    else:
                        sys.stderr.write("Unhandled story_cta: " + str(thing) + "!\n")

            if len(links) > 0:
                extra += "Links:\n"
                for link in links:
                    extra += str(link) + "\n"


        entries.append({
            "url": "http://guid.instagram.com/" + item["id"],#url,
            "caption": caption,
            "extratext": extra,
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

    if "broadcast" in storiesjson and storiesjson["broadcast"]:
        item = storiesjson["broadcast"]
        date = datetime.datetime.fromtimestamp(int(item["published_time"]), None).replace(tzinfo=tzlocal())

        entries.append({
            "url": "http://guid.instagram.com/" + item["media_id"],
            "caption": "[LIVE]",
            "author": username,
            "date": date,
            "images": [],
            "videos": [{
                "image": item["cover_frame_url"],
                "video": item.get("dash_abr_playback_url") or item["dash_playback_url"],
                "live": True,
                "type": "dash"
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


def get_profilepic_entry(config, userinfo):
    url = None
    if "profile_pic_url_hd" in userinfo:
        url = userinfo["profile_pic_url_hd"]
    elif "profile_pic_url" in userinfo:
        url = userinfo["profile_pic_url"]
    else:
        sys.stderr.write("No profile pic!\n")
        return

    newurl = normalize_image(url)
    id_ = re.sub(r".*/([^.]*)\.[^/]*$", "\\1", newurl)

    return {
        "url": newurl,
        "caption": "[DP] " + str(id_),
        "author": userinfo["username"],
        "date": rssit.util.parse_date(-1),
        "images": [newurl],
        "videos": []
    }


def generate_uid(config, uid):
    userinfo = get_user_info(config, uid)
    feed = get_feed(config, userinfo["user"])

    ppentry = get_profilepic_entry(config, userinfo["user"])
    if ppentry:
        feed["entries"].append(ppentry)

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

    #decoded_user = get_user_page(config, user)
    decoded_user = get_user_info_by_username(config, user)

    if config["force_api"]:
        return generate_uid(config, str(decoded_user["id"]))

    feed = get_feed(config, decoded_user)

    ppentry = get_profilepic_entry(config, decoded_user)
    if ppentry:
        feed["entries"].append(ppentry)

    def paginate(f):
        total = config["count"]
        if config["count"] == -1:
            total = decoded_user["media"]["count"]

        maxid = None
        nodes = []
        console = False

        while len(nodes) < total:
            output = f(maxid)
            nodes.extend(output[0])
            #nodes.extend(f(maxid))
            if len(nodes) < total:
                sys.stderr.write("\rLoading media (%i/%i)... " % (len(nodes), total))
                console = True
            maxid = output[1]  #nodes[-1]["id"]

        if console:
            sys.stderr.write("\n")

        return nodes

    #nodes = decoded_user["media"]["nodes"]
    if config["use_media"]:
        nodes = get_user_media_by_username(config, user)
    else:
        def get_nodes(max_id):
            media = decoded_user["media"]
            if max_id:
                media = get_user_info_by_username(config, user, max_id=max_id)["media"]
            nodes = media["nodes"]
            page_info = media["page_info"]
            return (nodes, page_info["end_cursor"], page_info["has_next_page"])
        #nodes = paginate(lambda max_id: decoded_user["media"]["nodes"] if not max_id else get_user_info_by_username(config, user, max_id=max_id)["media"]["nodes"])
        nodes = paginate(get_nodes)

    for node in reversed(nodes):
        feed["entries"].append(get_entry_from_node(config, node, user))

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

    reelsjson = rssit.util.json_loads(reels_data)

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
            "value": False
        },

        "force_api": {
            "name": "Forces API",
            "description": "Forces the usage of the API",
            "value": False
        },

        "use_media": {
            "name": "Use /media/ endpoint",
            "description": "Uses the now-removed /media/?__a=1, which provides 20 feeds",
            "value": False
        }
    },

    "get_url": get_url,
    "process": process
}]
