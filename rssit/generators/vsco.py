# -*- coding: utf-8 -*-

import rssit.util
import rssit.rest
import pprint
import os.path
import re
import urllib.parse
import datetime

api = rssit.rest.API({
    "name": "vsco",
    "type": "json",
    "endpoints": {
        "profile": {
            "url": "https://vsco.co/api/3.0/medias/profile",
            "query": {
                "site_id": rssit.rest.Arg("uid", 1),
                "limit": rssit.rest.Arg("limit", 2),
                "cursor": rssit.rest.Arg("cursor", 3)
            },
            "headers": {
                "referer": "https://vsco.co/",
                "X-Client-Build": "1",
                "X-Client-Platform": "web",
                "Authorization": rssit.rest.Arg("token")
            }
        }
    }
})


username_to_uid_cache = rssit.util.Cache("username_to_uid", 48*60*60, 100)


def get_url(config, url):
    match = re.match(r"^(https?://)?(?:\w+\.)?vsco\.co/(?P<user>[^/]*)(?:/gallery)?(?:[?#].*)?$", url)

    if match is None:
        return

    return "/u/" + match.group("user")


def normalize_image(url):
    return re.sub(r"[?#].*$", "", url)


def image_to_entry(image):
    author = image.get("permaSubdomain", None)  # or gridName/grid_name, or uid_to_username[siteId/site_id]
    if author is None:
        author = image["perma_subdomain"]

    date = image.get("uploadDate", None)
    if date is None:
        date = image["upload_date"]

    updated_date = image.get("lastUpdated", None)
    if updated_date is None:
        updated_date = image["last_updated"]

    base_image = image.get("responsiveUrl", None)
    if base_image is None:
        base_image = image["responsive_url"]

    entry = {
        "url": image["permalink"],
        "author": author,
        "caption": image["description"],
        "date": rssit.util.localize_datetime(datetime.datetime.fromtimestamp(date / 1000.0)),
        "updated_date": rssit.util.localize_datetime(datetime.datetime.fromtimestamp(updated_date / 1000.0)),
        "images": [
            normalize_image("https://" + base_image)
        ],
        "videos": []
    }

    return entry


def generate_user(config, user):
    url = "https://vsco.co/" + user + "/gallery"

    data = rssit.util.download(url)

    match = re.search(r"<script>window\.__PRELOADED_STATE__ = (?P<json>{.*?})</script>", data.decode('utf8'))

    if match is None:
        return

    json_text = match.group("json")
    initial_json = rssit.util.json_loads(json_text)

    user_site = initial_json["sites"]["siteByUsername"][user]["site"]
    author = user_site["name"]  # should be the same as username
    description = user_site["description"]
    uid = user_site["id"]

    token = initial_json["users"]["currentUser"]["tkn"]

    dp = normalize_image(user_site["profileImage"])
    if dp == "https://rassets.vsco.co/avatars/avatar-other.png":
        dp = None

    image_ids = {}
    json_images = initial_json["entities"]["images"]
    for image_id in json_images:
        image_ids[image_id] = json_images[image_id]

    feed = {
        "title": author,
        "description": description,
        "url": "https://vsco.co/" + user,
        "author": user,
        "config": {
            "generator": "vsco"
        },
        "entries": []
    }

    if dp is not None:
        """feed["entries"].append({
            "caption": "[DP] " +
        })"""
        pass

    medias_parent = initial_json["medias"]["bySiteId"][str(uid)]
    medias = medias_parent["medias"]

    def get_entries(maxid):
        apioptions = {
            "uid": uid,
            "limit": config["page_count"],
            "token": token
        }

        if maxid is None:
            maxid = medias_parent["nextCursor"]

        if maxid is not None:
            apioptions["cursor"] = maxid

        response = api.run(config, "profile", **apioptions)

        next_cursor = response.get("next_cursor", None)
        has_next_page = (len(response["media"]) == config["page_count"]) and (next_cursor is not None)

        return (response["media"], next_cursor, has_next_page)

    if config["count"] < 0 or config["count"] > len(medias):
        new_medias = rssit.util.paginate(config, None, get_entries)
        medias += new_medias

    for media in medias:
        media_obj = media["image"]
        if type(media_obj) == str:
            media_obj = image_ids[media_obj]

        feed["entries"].append(image_to_entry(media_obj))

    return ("social", feed)


infos = [{
    "name": "vsco",
    "display_name": "VSCO",

    "endpoints": {
        "u": {
            "name": "User's feed",
            "process": lambda server, config, path: generate_user(config, path)
        }
    },

    "config": {
        "page_count": {
            "name": "Page count",
            "description": "Elements to query per page",
            "value": 14
        }
    },

    "get_url": get_url,
}]
