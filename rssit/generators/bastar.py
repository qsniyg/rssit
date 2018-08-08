# -*- coding: utf-8 -*-

import rssit.util
import rssit.rest
import pprint
import json
import os.path
import re
import urllib.parse

# auth:
# POST https://api.bastabastar.com/users/authentication
#   content-type: application/x-www-form-urlencoded
#   content-length: 278
#   accept-encoding: gzip,
#   user-agent: okhttp/3.8.0
#  form:
#   email: [email]
#   password: [sha256 of password]
#   authType: EMAIL
#   pushToken: [push token]

# https://api.bastabastar.com/users/me
# https://api.bastabastar.com/users/recommendations/unread
# https://api.bastabastar.com/users/contents/unread
# https://api.bastabastar.com/videos?pageNumber=0&pageSize=8&orderBy=realtime&sortBy=recency
# https://api.bastabastar.com/bastars?pageNumber=0&pageSize=20&orderBy=realtime
# https://api.bastabastar.com/videos?pageNumber=0&pageSize=30&orderBy=up_realtime&sortBy=ranking
# https://api.bastabastar.com/bastars/[uid]
# https://api.bastabastar.com/bastars/[uid]/follow
#   content-length: 0
# http://bastabastar.s3.amazonaws.com/profile/compressed/profileid.jpg
#   http://bastabastar.s3.amazonaws.com/profile/profileid.jpg
# https://api.bastabastar.com/users/tokens/validations
#   with x-innertainment
#   form:
#     token: x-innertainment token
#     pushToken: push token
#     versionCode: 50
#     platform: ANDROID
#   reply (json):
#     includes pushToken (looks to be the same?)
#     includes token (same again?)
#     set-cookie, although cookie is never used?
# POST https://api.bastabastar.com/videos/[vid]/hits
#  content-length: 0
# https://api.bastabastar.com/videos/[vid]
# https://api.bastabastar.com/search?query=skfo&pageNumber=0&pageSize=20
# https://api.bastabastar.com/tags
# https://api.bastabastar.com/
#   only accept-encoding and user-agent
#   returns large accept-charset and the content is "bastabastar"

api = rssit.rest.API({
    "type": "json",
    "headers": {
        #"x-innertainment-auth-token": rssit.rest.Arg("auth-token", 0),
        "accept-encoding": "gzip",
        "user-agent": "okhttp/3.8.0"
    },
    "http_noextra": True,
    "endpoints": {
        "authentication": {
            "url": "https://api.bastabastar.com/users/authentication",
            "method": "POST",
            "form": {
                "email": rssit.rest.Arg("email", 0),
                "password": rssit.rest.Arg("password", 1),
                "authType": "EMAIL",
                "pushToken": rssit.rest.Arg("push-token", 2)
            }
        },
        "user": {
            "url": rssit.rest.Format("https://api.bastabastar.com/bastars/%s",
                                     rssit.rest.Arg("uid", 0)),
            "headers": {
                "x-innertainment-auth-token": rssit.rest.Arg("auth-token", 1)
            }
        },
        "search": {
            "url": "https://api.bastabastar.com/search",
            "headers": {
                "x-innertainment-auth-token": rssit.rest.Arg("auth-token", 10)
            },
            "query": {
                "query": rssit.rest.Arg("query", 0),
                "pageNumber": rssit.rest.Arg("pageNumber", 1),
                "pageSize": rssit.rest.Arg("pageSize", 2),
            }
        },
        "bastars": {
            "url": "https://api.bastabastar.com/bastars",
            "headers": {
                "x-innertainment-auth-token": rssit.rest.Arg("auth-token", 10)
            },
            "query": {
                "pageNumber": rssit.rest.Arg("pageNumber", 1),
                "pageSize": rssit.rest.Arg("pageSize", 2),
                "orderBy": rssit.rest.Arg("orderBy", 0)
            }
        }
    }
})

login_cache = rssit.util.Cache("bastar_login", 0, 0)


def login(config):
    config["http_resp"] = None
    try:
        response = api.run(config, "authentication", config["email"], config["password_hash"], config["push_token"])
        login_cache.add("auth_resp", response)
        login_cache.add("auth_token", response["token"])
        login_cache.add("push_token", response["pushToken"])
        return response
    except Exception as e:
        raise e


def login_if_needed(config):
    if not login_cache.get("auth_token"):
        login(config)


def get_tokens(config):
    auth = login_cache.get("auth_token")
    if not auth:
        login(config)
    return (auth, login_cache.get("push_token"))


def run_api(config, *args, **kwargs):
    auth, push = get_tokens(config)
    newkwargs = rssit.util.simple_copy(kwargs)
    newkwargs["push-token"] = push
    newkwargs["auth-token"] = auth
    return api.run(config, *args, **newkwargs)


def generate_login(server, config, path):
    return ("raw", login(config))


def generate_search(server, config, path):
    pageno = 0
    pagesize = 20
    if "pageNumber" in config and config["pageNumber"]:
        pageno = config["pageNumber"]
    if "pageSize" in config and config["pageSize"]:
        pagesize = config["pageSize"]

    response = run_api(config, "search", query=urllib.parse.unquote(path), pageNumber=pageno, pageSize=pagesize)
    pprint.pprint(response)

    return ("raw", response)


def generate_bastars(server, config, path):
    pageno = 0
    pagesize = 20
    orderby = "realtime"
    nofollow = False
    if "pageNumber" in config and config["pageNumber"]:
        pageno = config["pageNumber"]
    if "pageSize" in config and config["pageSize"]:
        pagesize = config["pageSize"]
    if "orderBy" in config and config["orderBy"]:
        orderby = config["orderBy"]
    if "nofollow" in config and config["nofollow"]:
        nofollow = True

    response = run_api(config, "bastars", pageNumber=pageno, pageSize=pagesize, orderBy=orderby)
    #pprint.pprint(response)

    newresponse = []
    for item in response:
        if nofollow and item["followed"]:
            continue
        newresponse.append(item)

    pprint.pprint(newresponse)

    return ("raw", newresponse)


def generate_user(server, config, path):
    try:
        response = run_api(config, "user", path)
    except Exception as e:
        # try logging in again
        if config["http_error"] == 403:
            login(config)
            response = run_api(config, "user", path)

    if "raw" in config and config["raw"]:
        return ("raw", response)

    name = response["name"]
    author = str(response["id"]) + " " + name

    feed = {
        "title": name,
        "author": author,
        "description": response["introductionWriting"],
        "url": "https://uid.bastabastar.com/" + str(response["id"]),
        "config": {
            "generator": "bastar"
        },
        "entries": []
    }

    if "signImageUrl" in response and response["signImageUrl"] is not None:
        guid = re.sub(r".*_([-0-9a-f]+)\.[^/.]*$", "\\1", os.path.basename(response["signImageUrl"]))
        feed["entries"].append({
            "caption": "[SIGNATURE] " + guid,
            "guid": "https://guid.bastabastar.com/sign/" + os.path.basename(response["signImageUrl"]),
            "url": response["signImageUrl"],
            "author": author,
            "date": rssit.util.parse_date(-1),
            "images": [response["signImageUrl"]],
            "videos": []
        })

    if "pictures" in response:
        for picture in response["pictures"]:
            date = rssit.util.replace_timezone(rssit.util.parse(picture["createdAt"]), "Asia/Seoul")
            url = urllib.parse.unquote(picture["imageUrl"]).replace("+", "%20")
            feed["entries"].append({
                "caption": "[PICTURE] " + str(picture["id"]),
                "guid": "https://guid.bastabastar.com/picture/" + str(picture["id"]),
                "url": url,
                "author": author,
                "date": date,
                "images": [url],
                "videos": []
            })

    if "otherVideoListOfThisBastarOrderByRecency" in response:
        for video in response["otherVideoListOfThisBastarOrderByRecency"]:
            date = rssit.util.replace_timezone(rssit.util.parse(video["createdAt"]), "Asia/Seoul")
            entry = {
                "caption": "[VIDEO] " + video["name"] + "\n\n" + video["description"],
                "guid": "https://guid.bastabastar.com/video/" + str(video["id"]),
                "url": video["videoUrl"],
                "author": author,
                "date": date,
                "images": [],
                "videos": [{
                    "image": video["thumbnailUrl"],
                    "video": video["videoUrl"]
                }]
            }
            if "updatedAt" in video and video["updatedAt"]:
                updated_date = rssit.util.replace_timezone(rssit.util.parse(video["updatedAt"]), "Asia/Seoul")
                entry["updated_date"] = updated_date
            feed["entries"].append(entry)

    if "profileImgUrl" in response:
        guid = re.sub(r"(.+)\.[^/.]*$", "\\1", os.path.basename(response["profileImgUrl"]))
        feed["entries"].append({
            "caption": "[DP] " + guid,
            "guid": "https://guid.bastabastar.com/sign/" + os.path.basename(response["profileImgUrl"]),
            "url": response["profileImgUrl"],
            "author": author,
            "date": rssit.util.parse_date(-1),
            "images": [response["profileImgUrl"]],
            "videos": []
        })

    return ("social", feed)


infos = [{
    "name": "bastar",
    "display_name": "Bastar",

    "endpoints": {
        "user": {
            "name": "User",
            "process": generate_user
        },
        "search": {
            "name": "Search",
            "process": generate_search
        },
        "bastars": {
            "name": "Bastars",
            "process": generate_bastars
        },
        "login": {
            "name": "Login",
            "process": generate_login
        }
    },

    "config": {
        "email": {
            "name": "Email",
            "description": "Email address you use to login with",
            "value": None
        },
        "password_hash": {
            "name": "Password hash",
            "description": "Password hashed by SHA-256", # echo -n password | sha256sum
            "value": None
        },
        "push_token": {
            "name": "Push token",
            "description": "Push token",
            "value": None
        },
        "auth_token": {
            "name": "Auth token",
            "description": "Auth token (unnecessary)",
            "value": None
        }
    }
}]
