# -*- coding: utf-8 -*-


import facebook
import requests
import pprint
from dateutil.parser import parse
import re


graphs = {}
#user_infos = {}
#albums = {}


def get_url(config, url):
    match = re.match(r"^(https?://)?(?:\w+\.)?facebook.com/(?P<user>[^/]*)/?(?P<photos>photos)?(/.*?)?$", url)

    if match is None:
        return

    if match.group("photos"):
        return "/photos/" + match.group("user")

    return "/user/" + match.group("user")


def get_api(access_token):
    global graphs
    if access_token not in graphs:
        graphs[access_token] = facebook.GraphAPI(access_token)

    return graphs[access_token]


def get_user_info(graph, user):
    #global user_infos
    user_infos = {}
    if user not in user_infos:
        user_infos[user] = graph.get_object(user + "?fields=name,username,about,description,link")
        #user_infos[user] = graph.get_object(user + "?fields=name,about,link")

        if "username" not in user_infos and "name" in user_infos:
            user_infos["username"] = user_infos["name"]

    return user_infos[user]


def get_feed_info(user_info, config):
    username = user_info.get("username", user_info.get("name", None))

    if not config["author_username"] and "name" in user_info and len(user_info["name"]) > 0:
        user = user_info["name"]
    else:
        user = username

    if "about" in user_info:
        description = user_info["about"]
    elif "description" in user_info:
        description = user_info["description"]
    else:
        description = user + "'s facebook"

    return {
        "title": user,
        "description": description,
        "author": username,
        "url": user_info["link"],
        "social": True,
        "entries": []
    }


def get_albumid_from_link(link):
    return re.match(r".*facebook\.com/[^/]*/photos/a\.([0-9]*).*", link).group(1)


def generate_photos(graph, config, user_info):
    #global albums
    albums = {}

    entries = []

    photos_api = graph.get_connections(user_info['id'], 'photos/uploaded?limit=100&fields=link,name,updated_time,images')
    photos = photos_api["data"]

    unnamed_ids = {}

    username = user_info.get("username", user_info.get("name", None))

    for photo in photos:
        albumid = get_albumid_from_link(photo["link"])

        if albumid not in albums:
            albums[albumid] = graph.get_object(albumid + "?fields=name,created_time")

        album = albums[albumid]

        if albumid not in unnamed_ids:
            unnamed_ids[albumid] = {}

        album_unnamed = unnamed_ids[albumid]

        albumname = album["name"]
        albumdate = parse(album["created_time"])
        albumdatestr = str(albumdate.year)[-2:] + str(albumdate.month).zfill(2) + str(albumdate.day).zfill(2)
        albumdatestr += ":"
        albumdatestr += str(albumdate.hour).zfill(2) + str(albumdate.minute).zfill(2) + str(albumdate.second).zfill(2)
        newalbumname = "(" + albumdatestr + ") " + albumname

        date = parse(photo["updated_time"])

        image = photo["images"][0]["source"]

        if "name" in photo:
            caption = photo["name"]
            media_caption = caption
        else:
            caption = ""

            if photo["updated_time"] in album_unnamed:
                unnamed_id = album_unnamed[photo["updated_time"]]
            else:
                album_unnamed[photo["updated_time"]] = 0
                unnamed_id = 0

            media_caption = "unnamed " + str(unnamed_id)

            album_unnamed[photo["updated_time"]] += 1

        entries.append({
            "url": photo["link"],
            "caption": caption,
            "media_caption": media_caption,
            "date": date,
            "album": newalbumname,
            "author": username,
            "images": [image],
            "videos": []
        })

    return entries


def generate_posts(graph, config, user_info):
    entries = []

    posts_api = graph.get_connections(user_info['id'], 'posts?limit=100&fields=id,message,created_time,updated_time,permalink_url,picture')
    posts = posts_api["data"]

    username = user_info.get("username", user_info.get("name", None))

    for post in posts:
        if "message" in post:
            caption = post["message"]
        else:
            caption = ""

        media_caption = "[POST] " + caption

        url = None  # post["permalink_url"]
        if "permalink_url" not in post or not url or len(url) <= 0:
            url = "https://www.facebook.com/" + username + "/posts/" + post["id"].split("_")[1]
        else:
            url = post["permalink_url"]

        date = parse(post["created_time"])
        updated_date = parse(post["updated_time"])

        images = []
        if "picture" in post:
            images = [post["picture"]]

        entries.append({
            "url": url,
            "author": username,
            "caption": caption,
            "media_caption": media_caption,
            "date": date,
            "updated_date": updated_date,
            "images": images,
            "videos": [],
            "album": "Posts"
        })

    return entries


def process(server, config, path):
    if path.startswith("/access_app"):
        access_token = facebook.GraphAPI().get_app_access_token(
            config["app_id"],
            config["app_secret"]
        )

        server.send_response(200, "OK")
        server.end_headers()

        server.wfile.write(bytes(access_token, "UTF-8"))
        return True

    if path.startswith("/access_2"):
        if not "code" in config:
            server.send_response(500, "ISE")
            server.end_headers()

            server.wfile.write(bytes("Need code", "UTF-8"))
            return True

        server.send_response(200, "OK")
        server.end_headers()

        token = facebook.GraphAPI().get_access_token_from_code(
            config["code"],
            config["redirect_url"],
            config["app_id"],
            config["app_secret"]
        )

        server.wfile.write(bytes(token["access_token"], "UTF-8"))
        return True

    if path.startswith("/access"):
        url = "https://www.facebook.com/v2.8/dialog/oauth?client_id=%s&redirect_uri=%s" % (
            config["app_id"],
            config["redirect_url"]
        )

        server.send_response(301, "Moved")
        server.send_header("Location", url)
        server.end_headers()

        return True

    graph = get_api(config["access_token"])

    if not graph:
        return None

    if path.startswith("/user/"):
        user = path[len("/user/"):]
        user_info = get_user_info(graph, user)

        feed = get_feed_info(user_info, config)

        feed["entries"] = generate_posts(graph, config, user_info)
        feed["entries"].extend(generate_photos(graph, config, user_info))

        return ("social", feed)
    if path.startswith("/photos/"):
        user = path[len("/photos/"):]
        user_info = get_user_info(graph, user)

        feed = get_feed_info(user_info, config)

        feed["entries"] = generate_photos(graph, config, user_info)

        return ("social", feed)
    elif path.startswith("/posts/"):
        user = path[len("/posts/"):]
        user_info = get_user_info(graph, user)

        feed = get_feed_info(user_info, config)

        feed["entries"] = generate_posts(graph, config, user_info)

        return ("social", feed)


infos = [{
    "name": "facebook",
    "display_name": "Facebook",

    "config": {
        "author_username": {
            "name": "Author = Username",
            "description": "Set the author's name to be their username",
            "value": False
        },

        "access_token": {
            "name": "Access Token",
            "description": "Facebook Access Token",
            "value": ""
        },

        "app_id": {
            "name": "App ID",
            "description": "Facebook App ID",
            "value": ""
        },

        "app_secret": {
            "name": "App Secret",
            "description": "Facebook App Secret",
            "value": ""
        },

        "redirect_url": {
            "name": "Redirect URL",
            "description": "Facebook App Redirect URL",
            "value": "" # /f/facebook/access_2
        }
    },

    "get_url": get_url,
    "process": process
}]
