# -*- coding: utf-8 -*-


import re
import rssit.util
import rssit.rest
import datetime
import sys
import pprint
import urllib.parse
from dateutil.tz import *
import collections
import traceback


instagram_ua = "Instagram 10.26.0 (iPhone7,2; iOS 10_1_1; en_US; en-US; scale=2.00; gamut=normal; 750x1334) AppleWebKit/420+"

endpoint_getentries = "https://www.instagram.com/graphql/query/?query_id=17888483320059182&variables="
endpoint_getstories = "https://www.instagram.com/graphql/query/?query_id=17873473675158481&variables="

# new endpoints:
# get entries
#   https://www.instagram.com/graphql/query/?query_hash=472f257a40c653c64c666ce877d59d2b&variables=%7B%22id%22%3A%222523526502%22%2C%22first%22%3A12%2C%22after%22%3A%22...%22%7D
#     query_hash:472f257a40c653c64c666ce877d59d2b
#     variables:{"id":"2523526502","first":12,"after":"..."}
#
# get all stories
#   https://www.instagram.com/graphql/query/?query_hash=b40536160b85d87aecc43106a1f35495&variables=%7B%7D
#     query_hash:b40536160b85d87aecc43106a1f35495
#     variables:{}
#
# get specific stories
#   https://www.instagram.com/graphql/query/?query_hash=15463e8449a83d3d60b06be7e90627c7&variables=%7B%22reel_ids%22%3A%5B%2212345%22%2C%2267890%22%5D%2C%22precomposed_overlay%22%3Afalse%7D
#      query_hash:15463e8449a83d3d60b06be7e90627c7
#      variables: {
#                   "reel_ids": [
#                     "12345",
#                     "67890"
#                     ...
#                   ],
#                   "precomposed_overlay": false
#                 }
#
# get comments
#   https://www.instagram.com/graphql/query/?query_hash=a3b895bdcb9606d5b1ee9926d885b924&variables=%7B%22shortcode%22%3A%22...%22%2C%22first%22%3A20%2C%22after%22%3A%22...%22%7D
#     query_hash:a3b895bdcb9606d5b1ee9926d885b924
#     variables: {"shortcode":"...","first":20,"after":"..."}



# others:
# descriptions are from personal observation only, could be wrong
#
# homepage items + stories
#   https://www.instagram.com/graphql/query/?query_id=17842794232208280&fetch_media_item_count=10&has_stories=true
#   https://www.instagram.com/graphql/query/?query_hash=253f5079497e7ef2756867645f972e4c&fetch_media_item_count=10&has_stories=true
#
# user suggestions based off another user
#   https://www.instagram.com/graphql/query/?query_id=17845312237175864&id=[uid]
#
# user suggestions
#   https://www.instagram.com/graphql/query/?query_id=17847560125201451&fetch_media_count=20
#
# stories?
#   https://www.instagram.com/graphql/query/?query_id=17890626976041463
#   https://www.instagram.com/graphql/query/?query_hash=b40536160b85d87aecc43106a1f35495
#
# likes
#   https://www.instagram.com/graphql/query/?query_id=17864450716183058&shortcode=[shortcode]&first=20
#
# user followed by
#   https://www.instagram.com/graphql/query/?query_id=17851374694183129&id=[uid]&first=20
#
# user following
#   https://www.instagram.com/graphql/query/?query_id=17874545323001329&id=[uid]&first=20
#
# comments
#   https://www.instagram.com/graphql/query/?query_id=17852405266163336&shortcode=[shortcode]&first=20&after=[commentid]
#
# edge_web_discover_media
#   https://www.instagram.com/graphql/query/?query_id=17863787143139595
#
# hashtag search
#   https://www.instagram.com/graphql/query/?query_id=17875800862117404&tag_name=[hashtag]&first=20
#
# get location info (+media & top posts)
#   https://www.instagram.com/graphql/query/?query_id=17865274345132052&id=[location id]&first=20
#
# saved media
#   https://www.instagram.com/graphql/query/?query_id=17885113105037631&id=[uid]&first=20
#
# contact_history
#   https://www.instagram.com/graphql/query/?query_id=17884116436028098


post_cache = rssit.util.Cache(60*60, 20)
uid_to_username_cache = rssit.util.Cache(6*60*60, 100)


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
    url = re.sub(r"(cdninstagram\.com/[^/]*/)s[0-9]*x[0-9]*/", "\\1", url)
    return url"""

    urlsplit = urllib.parse.urlsplit(url)
    urlstart = urlsplit.scheme + "://" + urlsplit.netloc + "/"

    pathsplit = urlsplit.path.split("/")

    have_t = False

    for i in pathsplit:
        if re.match(r"^t[0-9]+\.[0-9]+-[0-9]+$", i):
            urlstart += i + "/"
            have_t = True
        elif re.match(r"^[0-9_]*_[a-z]+\.[a-z0-9]+$", i):
            if not have_t:
                urlstart += "/"
            urlstart += i

    return urlstart


def base_image(url):
    return re.sub(r"\?[^/]*$", "", url)


def image_basename(url):
    return re.sub(r".*/([^.]*\.[^/]*)$", "\\1", base_image(url))


def parse_webpage_request(orig_config, config, data):
    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare is None:
        sys.stderr.write("No sharedData!\n")
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = rssit.util.json_loads(jsondata)

    return decoded


def parse_a1_request(orig_config, config, data):
    try:
        data = rssit.util.json_loads(data)
    except Exception as e:
        if str(data).startswith("<!"):
            orig_config["http_error"] = 404
        raise e

    return data


web_api = rssit.rest.API({
    "type": "json",
    "endpoints": {
        "webpage": {
            "url": rssit.rest.Format("http://www.instagram.com/%s/", rssit.rest.Arg("path", 0)),
            "parse": parse_webpage_request,
            "type": "raw"
        },

        "a1": {
            "url": rssit.rest.Format("http://www.instagram.com/%s/", rssit.rest.Arg("path", 0)),
            "parse": parse_a1_request,
            "type": "raw",
            "query": {
                "__a": 1
            }
        },

        "node": {
            "base": "webpage",
            "args": {
                "path": rssit.rest.Format("p/%s", rssit.rest.Arg("node", 0))
            }
        },

        "node_a1": {
            "base": "a1",
            "args": {
                "path": rssit.rest.Format("p/%s", rssit.rest.Arg("node", 0))
            }
        }
    }
})

graphql_id_api = rssit.rest.API({
    "type": "json",
    "url": "https://www.instagram.com/graphql/query/",
    "endpoints": {
        "base": {
            "query": {
                "variables": rssit.rest.Arg("variables", 0, parse=lambda x: rssit.util.json_dumps(x))
            }
        },

        "entries": {
            "base": "base",
            "query": {
                "query_id": "17888483320059182"
            }
        },

        "stories": {
            "base": "base",
            "query": {
                "query_id": "17873473675158481"
            }
        },

        "comments": {
            "base": "base",
            "query": {
                "query_id": "17852405266163336"
            }
        }
    }
})

graphql_hash_api = rssit.rest.API({
    "type": "json",
    "url": "https://www.instagram.com/graphql/query/",
    "endpoints": {
        "base": {
            "query": {
                "variables": rssit.rest.Arg("variables", 0, parse=lambda x: rssit.util.json_dumps(x))
            }
        },

        "entries": {
            "base": "base",
            "query": {
                "query_hash": "472f257a40c653c64c666ce877d59d2b"
            }
        },

        "stories": {
            "base": "base",
            "query": {
                "query_hash": "15463e8449a83d3d60b06be7e90627c7"
            }
        },

        "comments": {
            "base": "base",
            "query": {
                "query_hash": "a3b895bdcb9606d5b1ee9926d885b924"
            }
        }
    }
})

app_api = rssit.rest.API({
    "type": "json",
    "headers": {
        "User-Agent": instagram_ua,
        "x-ig-capabilities": "36oD",
        "accept": "*/*",
        # "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.8"
    },
    "endpoints": {
        "stories": {
            "url": rssit.rest.Format("https://i.instagram.com/api/v1/feed/user/%s/story/",
                                     rssit.rest.Arg("uid", 0))
        },
        "reels_tray": {
            "url": "https://i.instagram.com/api/v1/feed/reels_tray/"
        },
        "news": {
            "url": "https://i.instagram.com/api/v1/news/"
        },
        "user_info": {
            "url": rssit.rest.Format("https://i.instagram.com/api/v1/users/%s/info/",
                                     rssit.rest.Arg("uid", 0))
        },
        "user_feed": {
            "url": rssit.rest.Format("https://i.instagram.com/api/v1/feed/user/%s/",
                                     rssit.rest.Arg("uid", 0)),
            "query": {
                "max_id": rssit.rest.Arg("max_id", 1)
            }
        },
        "inbox": {
            "url": "https://i.instagram.com/api/v1/direct_v2/inbox/",
            "query": {
                "persistentBadging": "true",
                "use_unified_inbox": "true"
            }
        }
    }
})


"""
def do_a1_request(config, endpoint, *args, **kwargs):
    url = "http://www.instagram.com/" + endpoint.strip("/") + "/?__a=1"
    if "extra" in kwargs and kwargs["extra"]:
        url += "&" + kwargs["extra"]
    newdl = rssit.util.download(url, config=config)
    return rssit.util.json_loads(newdl)


def get_node_info_a1(config, code):
    return do_a1_request(config, "/p/" + code)


def get_node_info_webpage(config, code):
    req = do_website_request(config, "http://www.instagram.com/p/" + code)
    return req["entry_data"]["PostPage"][0]
"""


def do_a1_request(config, endpoint, *args, **kwargs):
    return web_api.run(config, "a1", endpoint.strip("/"), _overlay={"query": kwargs})


def get_node_info_a1(config, code):
    return web_api.run(config, "node_a1", code)


def get_node_info_webpage(config, code):
    req = web_api.run(config, "node", code)
    return req["entry_data"]["PostPage"][0]


def get_node_info(config, code):
    info = post_cache.get(code)
    if info:
        return info
    else:
        try:
            if config["use_shortcode_a1"]:
                req = get_node_info_a1(config, code)
            else:
                req = get_node_info_webpage(config, code)
            post_cache.add(code, req)
            return req
        except Exception as e:
            #print(e)
            traceback.print_exc()
            return {}


def get_node_media(config, node, images, videos):
    if len(node) == 0:
        return node

    node = normalize_node(node)

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
            #if base_image(image) == base_image(normalized):
            if image_basename(image) == image_basename(normalized):
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
            if len(newnodes) > 0:
                get_node_media(config, newnodes["graphql"]["shortcode_media"], images, videos)


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


def do_app_request(config, endpoint, **kwargs):
    if not has_cookie(config):
        return None

    return app_api.run(config, endpoint, **kwargs)
    #config = get_app_headers(config)
    #data = rssit.util.download(endpoint, config=config, http_noextra=True)
    #return rssit.util.json_loads(data)


def do_graphql_request(config, endpoint, variables):
    if config["use_hash_graphql"]:
        retval = graphql_hash_api.run(config, endpoint, variables)
    else:
        retval = graphql_id_api.run(config, endpoint, variables)
    #pprint.pprint(retval)
    return retval
    #data = rssit.util.download(endpoint, config=config)
    #return rssit.util.json_loads(data)


def get_stories_app(config, userid):
    return do_app_request(config, "stories", uid=userid)
    #storiesurl = "https://i.instagram.com/api/v1/feed/user/" + userid + "/story/"
    #return do_app_request(config, storiesurl)


def get_stories_graphql(config, userid):
    variables = {
        "reel_ids": [userid],
        "precomposed_overlay": False
    }
    return do_graphql_request(config, "stories", variables)
    #storiesurl = endpoint_getstories + urllib.parse.quote(rssit.util.json_dumps(variables))
    #return do_graphql_request(config, storiesurl)


def get_reelstray_app(config):
    return do_app_request(config, "reels_tray")
    #storiesurl = "https://i.instagram.com/api/v1/feed/reels_tray/"
    #return do_app_request(config, storiesurl)


def get_user_info(config, userid):
    return do_app_request(config, "user_info", uid=userid)
    #return do_app_request(config, "https://i.instagram.com/api/v1/users/" + userid + "/info/")


def get_user_info_by_username_a1(config, username, *args, **kwargs):
    extra = {}
    if "max_id" in kwargs and kwargs["max_id"]:
        #extra = "max_id=" + str(kwargs["max_id"])
        extra = {
            "max_id": str(kwargs["max_id"])
        }
    return do_a1_request(config, username, **extra)["user"]


def get_user_info_by_username_website(config, username):
    return get_user_page(config, username)


def get_user_info_by_username(config, username, *args, **kwargs):
    if "use_profile_a1" in config and config["use_profile_a1"]:
        return get_user_info_by_username_a1(config, username, *args, **kwargs)
    else:
        return get_user_info_by_username_website(config, username)


def get_user_media_by_username(config, username):
    return do_a1_request(config, username + "/media")["items"]


def do_website_request(config, url):
    data = rssit.util.download(url, config=config)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare is None:
        sys.stderr.write("No sharedData!\n")
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = rssit.util.json_loads(jsondata)

    return decoded

def get_user_page(config, username):
    url = "https://www.instagram.com/" + username + "/"  # / to avoid redirect

    """data = rssit.util.download(url, config=config)

    jsondatare = re.search(r"window._sharedData = *(?P<json>.*?);?</script>", str(data))
    if jsondatare is None:
        sys.stderr.write("No sharedData!\n")
        return None

    jsondata = bytes(jsondatare.group("json"), 'utf-8').decode('unicode-escape')
    decoded = rssit.util.json_loads(jsondata)"""

    decoded = do_website_request(config, url)

    return decoded["entry_data"]["ProfilePage"][0]["user"]


def get_nodes_from_uid_graphql(config, uid, *args, **kwargs):
    variables = {
        "id": uid,
        "first": 12
    }

    for arg in kwargs:
        if kwargs[arg] is not None:
            variables[arg] = kwargs[arg]

    jsondumped = rssit.util.json_dumps(variables)
    url = endpoint_getentries + urllib.parse.quote(jsondumped)
    #return do_graphql_request(config, url)
    return do_graphql_request(config, "entries", variables)
    #config = get_app_headers(config)
    #data = rssit.util.download(url, config=config, http_noextra=True)
    #decoded = rssit.util.json_loads(data)
    #return decoded


def get_nodes_from_uid_app(config, uid, *args, **kwargs):
    newargs = {
        "uid": uid
    }

    if "max_id" in kwargs and kwargs["max_id"]:
        newargs["max_id"] = kwargs["max_id"]

    return do_app_request(config, "user_feed", **newargs)
    #url = "https://i.instagram.com/api/v1/feed/user/" + uid + "/"
    #if "max_id" in kwargs and kwargs["max_id"]:
    #    url += "?max_id=" + kwargs["max_id"]
    #return do_app_request(config, url)


def force_array(obj):
    if type(obj) == dict:
        a = []
        for i in obj:
            a.append(obj[i])
        return a
    return obj


def get_largest_url(items):
    max_ = 0
    url = None
    for item in force_array(items):
        if "height" in item:
            total = item["height"] + item["width"]
        elif "config_height" in item:
            total = item["config_height"] + item["config_width"]
        if total > max_:
            max_ = total

            if "url" in item:
                url = item["url"]
            else:
                url = item["src"]
    return url


def get_stories(config, userid):
    if not config["use_graphql_stories"]:
        stories = get_stories_app(config, userid)
    else:
        oldstories = get_stories_graphql(config, userid)
        reels_media = oldstories["data"]["reels_media"]

        if len(reels_media) > 0:
            stories = {
                "reel": oldstories["data"]["reels_media"][0]
            }
        else:
            stories = {"reel": None}
    return stories


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
        elif "taken_at" in node:
            node["date"] = node["taken_at"]

    if "code" not in node:
        if "shortcode" in node:
            node["code"] = node["shortcode"]

    if "type" not in node:
        if "__typename" in node:
            if node["__typename"] in ["GraphImage", "GraphStoryImage"]:
                node["type"] = "image"
            elif node["__typename"] in ["GraphVideo", "GraphStoryVideo"]:
                node["type"] = "video"
            elif node["__typename"] == "GraphSidecar":
                node["type"] = "carousel"

    if (("carousel_media" in node and type(node["carousel_media"]) == list and len(node["carousel_media"]) > 0)
        and ("type" in node and node["type"] != "carousel")):
        node["type"] = "carousel"

    if "video_url" not in node:
        base = None

        if "videos" in node:
            base = node["videos"]
        elif "video_resources" in node:
            base = node["video_resources"]
        elif "video_versions" in node:
            base = node["video_versions"]

        if base:
            new_url = get_largest_url(base)
            if new_url:
                node["video_url"] = new_url

            """max_ = 0
            for video in node["videos"]:
                total = video["height"] + video["width"]
                if total > max_:
                    max_ = total
                    node["video_url"] = video["url"]"""

    if "video_url" in node:
        node["video_url"] = normalize_image(node["video_url"])

    if "type" not in node:
        if "video_url" not in node:
            node["type"] = "image"
        else:
            node["type"] = "video"

    if "display_url" not in node:
        base = None

        if "images" in node:
            base = node["images"]
        elif "image_versions2" in node:
            base = node["image_versions2"]["candidates"]

        if base:
            new_url = get_largest_url(base)
            if new_url:
                node["display_url"] = new_url

            """new_url = get_largest_url(node["images"])
            if new_url:
                node["display_url"] = new_url"""

    if ("display_url" not in node) and ("carousel_media" in node):
        node["display_url"] = normalize_node(node["carousel_media"][0])["display_url"]

    if "display_url" in node:
        node["display_url"] = normalize_image(node["display_url"])

    if "is_video" not in node:
        node["is_video"] = node["type"] == "video"

    if node["type"] == "carousel" and "carousel_media" not in node:
        if "edge_sidecar_to_children" in node:
            node["carousel_media"] = []
            for newnode in node["edge_sidecar_to_children"]["edges"]:
                node["carousel_media"].append(newnode["node"])

    if "user" not in node:
        if "owner" in node:
            node["user"] = node["owner"]

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

        if len(newnodes) > 0:
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


def parse_story_entries(config, storiesjson, do_stories=True):
    if "reel" not in storiesjson or not storiesjson["reel"]:
        storiesjson["reel"] = {"items": []}

        if "tray" in storiesjson and type(storiesjson["tray"]) == list:
            for tray in storiesjson["tray"]:
                if "items" not in tray:
                    continue
                for item in tray["items"]:
                    storiesjson["reel"]["items"].append(item)

    if "post_live_item" not in storiesjson or not storiesjson["post_live_item"]:
        storiesjson["post_live_item"] = {"broadcasts": []}

        if (("post_live" in storiesjson and storiesjson["post_live"])
            and ("post_live_items" in storiesjson["post_live"]
                 and storiesjson["post_live"]["post_live_items"])):
            for item in storiesjson["post_live"]["post_live_items"]:
                if "broadcasts" in item and item["broadcasts"]:
                    for broadcast in item["broadcasts"]:
                        storiesjson["post_live_item"]["broadcasts"].append(broadcast)

    if "broadcasts" not in storiesjson or not storiesjson["broadcasts"]:
        storiesjson["broadcasts"] = []

        if "broadcast" in storiesjson and storiesjson["broadcast"]:
            storiesjson["broadcasts"].append(storiesjson["broadcast"])

    entries = []

    for item in storiesjson["reel"]["items"]:
        if not do_stories:
            break

        item = normalize_node(item)

        image = normalize_image(item["display_url"])

        url = image
        images = [image]
        videos = []

        if "video_url" in item and item["video_url"]:
            videos = [{
                "image": image,
                "video": item["video_url"]
            }]
            url = videos[0]["video"]
            images = []

        caption = "[STORY]"

        if "caption" in item and item["caption"]:
            caption = "[STORY] " + item["caption"]

        date = datetime.datetime.fromtimestamp(int(item["date"]), None).replace(tzinfo=tzlocal())

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
            "url": "http://guid.instagram.com/" + item["id"],  #url,
            "caption": caption,
            "extratext": extra,
            "author": uid_to_username(config, item["user"]),  #["username"],
            "date": date,
            "images": images,
            "videos": videos
        })

    for item in storiesjson["post_live_item"]["broadcasts"]:
        date = datetime.datetime.fromtimestamp(int(item["published_time"]), None).replace(tzinfo=tzlocal())

        entries.append({
            "url": "http://guid.instagram.com/" + item["media_id"],
            "caption": "[LIVE REPLAY]",
            "author": uid_to_username(config, item["broadcast_owner"]),  #["username"],
            "date": date,
            "images": [],
            "videos": [{
                "image": item["cover_frame_url"],
                "video": rssit.util.get_local_url("/f/instagram/livereplay/" + item["media_id"])
            }]
        })

    for item in storiesjson["broadcasts"]:
        date = datetime.datetime.fromtimestamp(int(item["published_time"]), None).replace(tzinfo=tzlocal())

        entries.append({
            "url": "http://guid.instagram.com/" + item["media_id"],
            "caption": "[LIVE]",
            "author": uid_to_username(config, item["broadcast_owner"]),  #["username"],
            "date": date,
            "images": [],
            "videos": [{
                "image": item["cover_frame_url"],
                "video": item.get("dash_abr_playback_url") or item["dash_playback_url"],
                "live": True,
                "type": "instagram_live"
            }]
        })

    return entries


def get_story_entries(config, uid, username):
    if not config["stories"]:
        return []

    try:
        storiesjson = get_stories(config, uid)

        if not storiesjson:
            sys.stderr.write("Warning: not logged in, so no stories\n")
            return []
    except Exception as e:  # soft error
        sys.stderr.write(str(e) + "\n")
        return []

    return parse_story_entries(config, storiesjson)


def get_reels_entries(config):
    storiesjson = get_reelstray_app(config)

    if not storiesjson:
        sys.stderr.write("Warning: not logged in, so no stories\n")
        return []

    return parse_story_entries(config, storiesjson, do_stories=False)


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
    id_withext = image_basename(newurl) # re.sub(r".*/([^.]*\.[^/]*)$", "\\1", newurl)

    return {
        "url": newurl,
        "caption": "[DP] " + str(id_),
        "author": userinfo["username"],
        "date": rssit.util.parse_date(-1),
        "guid": "https://scontent-sea1-1.cdninstagram.com//" + id_withext,
        "images": [newurl],
        "videos": []
    }


def generate_user(config, *args, **kwargs):
    config["httpheader_User-Agent"] = rssit.util.get_random_user_agent()

    if "username" in kwargs:
        username = kwargs["username"]

        if not config["use_profile_a1"]:
            decoded_user = get_user_page(config, username)
        else:
            decoded_user = get_user_info_by_username(config, username)

        uid = decoded_user["id"]
        mediacount = decoded_user["media"]["count"]
        medianodes = decoded_user["media"]["nodes"]
    elif "uid" in kwargs:
        uid = kwargs["uid"]
        decoded_user = get_user_info(config, uid)["user"]
        username = decoded_user["username"]

        mediacount = decoded_user["media_count"]
        medianodes = []

    feed = get_feed(config, decoded_user)

    ppentry = get_profilepic_entry(config, decoded_user)
    if ppentry:
        feed["entries"].append(ppentry)

    def paginate(f):
        total = config["count"]
        if config["count"] == -1:
            total = mediacount

        maxid = None
        nodes = []
        console = False
        has_next_page = True

        while (len(nodes) < total) and has_next_page:
            output = f(maxid)
            nodes.extend(output[0])
            if len(nodes) < total:
                sys.stderr.write("\rLoading media (%i/%i)... " % (len(nodes), total))
                sys.stderr.flush()
                console = True
            maxid = output[1]
            has_next_page = output[2]

        if console:
            sys.stderr.write("\n")
            sys.stderr.flush()

        return nodes

    count = config["count"]

    if count < 0:
        count = mediacount

    if config["use_media"]:
        nodes = get_user_media_by_username(config, username)
    elif config["use_graphql_entries"] and count > len(medianodes):
        # there doesn't seem to be a limit, but let's impose one just in case
        if count > 500:
            count = 500
        elif count == 1:
            count = 20

        def get_nodes(cursor):
            media = get_nodes_from_uid_graphql(config, uid, first=count, after=cursor)
            edges = media["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
            pageinfo = media["data"]["user"]["edge_owner_to_timeline_media"]["page_info"]

            nodes = []
            for node in edges:
                nodes.append(node["node"])

            return (nodes, pageinfo["end_cursor"], pageinfo["has_next_page"])

        nodes = paginate(get_nodes)
    elif config["use_api_entries"] and count > len(medianodes):
        def get_nodes(cursor):
            media = get_nodes_from_uid_app(config, uid, max_id=cursor)

            return (media["items"], media["next_max_id"], media["more_available"])
        nodes = paginate(get_nodes)
    else:
        def get_nodes(max_id):
            if max_id or "media" not in decoded_user:
                media = get_user_info_by_username(config, username, max_id=max_id)["media"]
            else:
                media = decoded_user["media"]
            nodes = media["nodes"]
            page_info = media["page_info"]

            end_cursor = page_info["end_cursor"]
            has_next_page = page_info["has_next_page"]

            if not config["use_profile_a1"]:
                end_cursor = None
                has_next_page = None

            return (nodes, end_cursor, has_next_page)
        nodes = paginate(get_nodes)

    for node in reversed(nodes):
        feed["entries"].append(get_entry_from_node(config, node, username))

    story_entries = get_story_entries(config, uid, username)
    for entry in story_entries:
        feed["entries"].append(entry)

    return ("social", feed)


def generate_reelstray(config):
    config["is_index"] = True

    feed = {
        "title": "Live streams",
        "description": "Live streams/replays (reels tray)",
        "url": "https://reelstray.instagram.com/",  # fake url for now
        "author": "instagram",
        "entries": []
    }

    feed["entries"] = get_reels_entries(config)

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


shortcode_arr = [chr(x) for x in range(ord('A'), ord('Z') + 1)]
shortcode_arr.extend([chr(x) for x in range(ord('a'), ord('z') + 1)])
shortcode_arr.extend([chr(x) for x in range(ord('0'), ord('9') + 1)])
shortcode_arr.extend(['-', '_'])


def to_shortcode(n):
    if n < 64:
        return shortcode_arr[n]
    else:
        return to_shortcode(n // 64) + shortcode_arr[n % 64]


def id_to_url(id):
    if "_" in id:
        id = id.split("_")[0]

    shortcode = to_shortcode(int(id))
    return "https://www.instagram.com/p/" + shortcode + "/"


def get_uid_from_id(id):
    return id.split("_")[1]


def normalize_user(user):
    if "uid" not in user:
        if "pk" in user:
            user["uid"] = user["pk"]
        elif "id" in user:
            user["uid"] = user["id"]

    return user


def uid_to_username(config, uid):
    real_uid = uid

    if type(uid) == dict:
        uid = normalize_user(rssit.util.simple_copy(uid))

        if "uid" in uid:
            real_uid = uid["uid"]
        elif "username" in uid:
            return uid["username"]
        else:
            return None

    if "debug" in config and config["debug"]:
        return real_uid

    username = uid_to_username_cache.get(real_uid)
    if not username:
        if type(uid) == dict and "username" in uid:
            username = uid["username"]
        else:
            userinfo = get_user_info(config, real_uid)
            username = userinfo["user"]["username"]
        uid_to_username_cache.add(real_uid, username)
    return username


def username_to_url(username):
    return "https://www.instagram.com/" + username + "/"


def uid_to_url(config, uid):
    return username_to_url(uid_to_username(config, uid))


def generate_convert(config, server, url):
    if url.startswith("uid/"):
        username = uid_to_username(config, url[len("uid/"):])

        server.send_response(301, "Moved")
        server.send_header("Location", "https://www.instagram.com/" + username)
        server.end_headers()

    return True


def generate_news_media(medias):
    content = ""
    for media in medias:
        content += "<p><a href='%s'><img src='%s' alt='(image)' /></a></p>" % (
            id_to_url(media["id"]),
            normalize_image(media["image"]),
        )

    return content


def generate_simple_news(config, story):
    args = story["args"]
    caption = args["text"]

    if "links" not in args:
        content = "<p>" + caption + "</p>"
    else:
        caption_parts = []
        last_end = 0

        for link in args["links"]:
            caption_parts.append(caption[last_end:link["start"]])

            if link["type"] == "user":
                caption_parts.append("<a href='%s'>%s</a>" % (
                    uid_to_url(config, link["id"]),
                    #rssit.util.get_local_url("/f/instagram/convert/uid/" + link["id"]),
                    caption[link["start"]:link["end"]]
                ))
            else:
                sys.stderr.write("Unhandled news type: " + link["type"] + "\n")
                caption_parts.append(caption[link["start"]:link["end"]])

            last_end = link["end"]

        caption_parts.append(caption[last_end:])

        content = "".join(caption_parts)
        content = "<p>" + content + "</p>"

    if "media" not in args:
        args["media"] = []

    content += generate_news_media(args["media"])

    return (caption, content)


def generate_news(config):
    #newsreq = do_app_request(config, "https://i.instagram.com/api/v1/news")
    newsreq = do_app_request(config, "news")

    if "raw" in config and config["raw"]:
        return ("feed", newsreq)

    config["no_dl"] = True

    feed = {
        "title": "News",
        "description": "Events happening in your Instagram feed",
        "url": "https://news.instagram.com/",  # fake url for now
        "author": "instagram",
        "entries": []
    }

    author = "instagram"

    for story in newsreq["stories"]:
        args = story["args"]

        story_type = story["story_type"]
        caption = args["text"]
        date = datetime.datetime.fromtimestamp(int(args["timestamp"]), None).replace(tzinfo=tzlocal())

        # story_type:
        # 12 = leave a comment
        # 13 = like comment
        # 60 = like post
        # 101 = started following
        # 128 = taking a video at n

        # type:
        # 1 = 1 person likes 1 post, or leave a comment on 1 post
        # 2 = 1 person likes n posts, or 'took n videos at n'
        # 4 = 1 person starts following 1-n other people
        # 14 = 1 person likes 1 comment

        subjs = []
        objs = []
        comments = {}

        link_users = []
        for link in args["links"]:
            if link["type"] == "user":
                link_users.append({
                    "uid": link["id"],
                    "username": caption[link["start"]:link["end"]]
                })

        if "media" in args and len(args["media"]) > 0:
            if len(args["media"]) > 1:
                # for "1 liked n of 2's posts."
                different_uids = False
                last_uid = None

                for media in args["media"]:
                    v = {
                        "media": media,
                        "uid": get_uid_from_id(media["id"])
                    }

                    if not last_uid:
                        last_uid = v["uid"]
                    elif v["uid"] != last_uid:
                        different_uids = True

                    objs.append(v)

                users = link_users
                if (len(args["media"]) > 1 and
                    len(link_users) > 1 and
                    not different_uids and
                    last_uid == link_users[-1]["uid"]):
                    users = link_users[:-1]

                for user in users:
                    subjs.append(user)
            elif "comment_ids" in args and len(args["comment_ids"]) > 1:
                # There are n comments on 1's post: @2: ...\n@3: ...
                # problem: only one user link (1, not 2 and 3)
                for user_i in range(len(link_users[1:])):
                    v = {
                        "comment": args["comment_ids"][user_i]
                    }
                    v.update(link_users[user_i])
                    subjs.append(v)

                v = {
                    "media": media,
                }
                v.update(link_users[0])
                objs.append(v)
            else:
                for user in link_users[:-1]:
                    subjs.append(user)
                v = {
                    "media": args["media"][0]
                }
                if "comment_id" in args:
                    v["comment"] = args["comment_id"]
                v.update(link_users[-1])
                objs.append(v)
        elif story_type == 101:
            subjs.append(link_users[0])
            objs.extend(link_users[1:])

        def add_simple():
            caption, content = generate_simple_news(config, story)
            feed["entries"].append({
                "url": "http://tuuid.instagram.com/tuuid:" + args["tuuid"],
                "title": caption,
                "author": author,
                "date": date,
                "content": content
            })

        if ((story_type != 12 and story_type != 13 and story_type != 60 and story_type != 101) or
            len(subjs) == 0 or
            len(objs) == 0 or
            ((story_type == 12 or story_type == 13) and len(args["media"]) > 1)):
            if story_type != 101 or True:
                sys.stderr.write("Possibly unhandled story_type: " + str(story_type) + "\n")
                if len(subjs) == 0 or len(objs) == 0:
                    sys.stderr.write("Unable to find subject(s) or object(s): " + pprint.pformat(story) + "\n")
            add_simple()
            continue

        if story_type == 12 or story_type == 13:
            lastpos = args["links"][-1]["end"]
            newcaption = caption[lastpos:]
            newcaption = newcaption[newcaption.index(":") + 1:]

            # There are n comments on 1's post: @2: ...\n@3: ...
            multi = len(args["comment_ids"]) > 1
            for comment_id_i in range(len(args["comment_ids"])):
                if multi:
                    newcaption = newcaption[newcaption.index(":") + 1:]

                if "\n" in newcaption:
                    curr = newcaption[:newcaption.index("\n")]
                else:
                    curr = newcaption

                #comments.push((comment_id, curr.strip()))
                comments[args["comment_ids"][comment_id_i]] = curr.strip()

                if len(newcaption) > (len(curr) + 1):
                    newcaption = newcaption[len(curr) + 1:]

        formatted = {
            12: "##1## left a comment on ##2##'s post: ",
            13: "##1## liked ##2##'s comment: ",
            60: "##1## liked ##2##'s post.",
            101: "##1## started following ##2##."
        }

        def uids_to_names(uids):
            if type(uids) != list:
                uids = [uids]

            links = []
            for uid in uids:
                username = uid_to_username(config, uid)
                links.append(username)

            return links

        def uids_to_links(uids):
            if type(uids) != list:
                uids = [uids]

            links = []
            for uid in uids:
                username = uid_to_username(config, uid)
                links.append("<a href='%s'>%s</a>" % (username_to_url(username), username))

            return links

        def english_array(array):
            if len(array) == 0:
                return ""

            if len(array) == 1:
                return array[0]

            text = ""
            for i in range(len(array)):
                if i == 0:
                    text += array[i]
                elif i + 1 == len(array):
                    text += " and " + array[i]
                else:
                    text += ", " + array[i]

            return text

        def do_format(func, subj, obj):
            text = formatted[story_type]
            text = text.replace("##1##", english_array(func(subj)))
            text = text.replace("##2##", english_array(func(obj)))

            if comment:
                text += comments[comment]

            return text

        comment = None
        media = None

        for subj in subjs:
            if "media" in subj:
                media = subj["media"]
            if "comment" in subj:
                comment = subj["comment"]

            for obj_i in range(len(objs)):
            #for media_i in range(len(args["media"])):
                obj = objs[obj_i]

                if "media" in obj:
                    media = obj["media"]
                if "comment" in obj:
                    comment = obj["comment"]

                #media = args["media"][obj_i]
                #obj = objs[obj_i]

                caption = do_format(uids_to_names, subj, obj)
                content = "<p>%s</p>" % do_format(uids_to_links, subj, obj)

                if media:
                    content += generate_news_media([media])

                tuuid = "story_type:%s/subject:%s" % (
                    #args["tuuid"],
                    story_type,
                    subj["uid"]
                )

                if media:
                    tuuid += "/media:%s" % media["id"]

                    if comment:
                        tuuid += "/comment_id:%s" % str(comment) #str(args["comment_id"])
                else:
                    tuuid += "/object:%s" % obj["uid"]

                feed["entries"].append({
                    "url": "http://tuuid.instagram.com/" + tuuid,
                    "title": caption,
                    "author": author,
                    "date": date,
                    "content": content
                })

        continue

        tuuid = args["tuuid"]
        tuuid += "/" + str(story["story_type"])

        if "comment_ids" in args and len(args["comment_ids"]):
            tuuid += "/" + str(args["comment_ids"][0])

        feed["entries"].append({
            "url": "http://tuuid.instagram.com/" + tuuid,
            "title": caption,
            "author": author,
            "date": date,
            "content": content
        })

    return ("feed", feed)


def generate_inbox(config):
    inboxreq = do_app_request(config, "inbox")

    if "raw" in config and config["raw"]:
        return ("feed", inboxreq)

    config["no_dl"] = True

    feed = {
        "title": "Inbox",
        "description": "Direct messages",
        "url": "http://inbox.instagram.com/",  # fake url for now
        "author": "instagram",
        "entries": []
    }

    for thread in inboxreq["inbox"]["threads"]:
        for user in thread["users"]:
            # cache
            uid_to_username(config, {
                "uid": user["pk"],
                "username": user["username"]
            })

        for item in thread["items"]:
            guid = item["item_id"]
            title = None
            content = None
            if "text" in item:
                content = item["text"]
                title = content
            elif "link" in item:
                content = item["link"]["text"]
                title = content
            elif "action_log" in item:
                content = "<em>%s</em>" % item["action_log"]["description"]
            if not content:
                content = "(n/a)"
            if not title:
                title = ""
            caption = "[" + thread["thread_title"] + "] " + title
            if item["user_id"] == thread["viewer_id"]:
                if True:
                    continue
            author = uid_to_username(config, item["user_id"])
            date = datetime.datetime.fromtimestamp(int(item["timestamp"])/1000000, None).replace(tzinfo=tzlocal())
            feed["entries"].append({
                "url": "http://guid.instagram.com/" + guid,
                "title": caption,
                "author": author,
                "date": date,
                "content": content
            })

    return ("feed", feed)


def generate_raw(config, path):
    if path.startswith("p/"):
        post = path[len("p/"):]
        #node = get_node_info_webpage(config, post)["graphql"]["shortcode_media"]
        node_raw = get_node_info(config, post)
        node = node_raw["graphql"]["shortcode_media"]
        node = normalize_node(node)

        images = []
        videos = []
        get_node_media(config, node, images, videos)

        node["node_images"] = images
        node["node_videos"] = videos

        comments = node["edge_media_to_comment"]
        after = comments["page_info"]["end_cursor"]

        def get_comments(maxid):
            if not maxid:
                maxid = after
            newcomments_api = do_graphql_request(config, "comments", {
                "shortcode": post,
                "first": 500,
                "after": maxid
            })["data"]["shortcode_media"]["edge_media_to_comment"]
            retval = (newcomments_api["edges"],
                    newcomments_api["page_info"]["end_cursor"],
                    newcomments_api["page_info"]["has_next_page"])
            return retval

        if after:
            morecomments = rssit.util.paginate(config, comments["count"], get_comments)
            comments["edges"] = comments["edges"] + morecomments
            comments["edges"].sort(key=lambda x: x["node"]["created_at"])
            #node["edge_media_to_comment"] = comments

        return ("raw", node)
    return None


def process(server, config, path):
    if path.startswith("/u/"):
        return generate_user(config, username=path[len("/u/"):])

    if path.startswith("/v/"):
        return generate_video(config, server, path[len("/v/"):])

    if path.startswith("/livereplay/"):
        return generate_livereplay(config, server, path[len("/livereplay/"):])

    if path.startswith("/uid/"):
        return generate_user(config, uid=path[len("/uid/"):])

    if path.startswith("/convert/"):
        return generate_convert(config, server, path[len("/convert/"):])

    if path.startswith("/news"):
        return generate_news(config)

    if path.startswith("/reels_tray"):
        return generate_reelstray(config)

    if path.startswith("/inbox"):
        return generate_inbox(config)

    return None


infos = [{
    "name": "instagram",
    "display_name": "Instagram",

    "endpoints": {
        "u": {
            "name": "User's feed by username",
            "process": lambda server, config, path: generate_user(config, username=path)
        },
        "v": {
            "name": "Redirect to the URL of a video",
            "internal": True,
            "process": lambda server, config, path: generate_video(config, server, path)
        },
        "livereplay": {
            "name": "Serve a live replay's DASH manifest",
            "internal": True,
            "process": lambda server, config, path: generate_livereplay(config, server, path)
        },
        "uid": {
            "name": "User's feed by UID",
            "process": lambda server, config, path: generate_user(config, uid=path)
        },
        "convert": {
            "name": "Convert between formats",
            "internal": True,
            "process": lambda server, config, path: generate_convert(config, server, path)
        },
        "news": {
            "name": "Events happening in your instagram feed",
            "process": lambda server, config, path: generate_news(config)
        },
        "reels_tray": {
            "name": "Live videos/replays",
            "process": lambda server, config, path: generate_reelstray(config)
        },
        "inbox": {
            "name": "Inbox",
            "process": lambda server, config, path: generate_inbox(config)
        },
        "raw": {
            "name": "Raw API access",
            "internal": True,
            "process": lambda server, config, path: generate_raw(config, path)
        }
    },

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

        "use_media": {
            "name": "Use /media/ endpoint",
            "description": "Uses the now-removed /media/?__a=1, which provides 20 feeds",
            "value": False
        },

        "use_profile_a1": {
            "name": "Use [profile]/?__a=1 endpoint",
            "description": "Uses the [profile]/?__a=1 endpoint, more prone to rate-limiting",
            "value": False
        },

        "use_shortcode_a1": {
            "name": "Use /p/[shortcode]/?__a=1 endpoint",
            "description": "Uses the /p/[shortcode]/?__a=1 endpoint, faster, but possibly more prone to rate-limiting",
            "value": False
        },

        "use_graphql_stories": {
            "name": "Use graphql stories",
            "description": "Uses graphql for stories instead of the app API. Less rate-limited, but less features (no livestreams, no caption, no click-to-action).",
            "value": False
        },

        "use_graphql_entries": {
            "name": "Use graphql entries",
            "description": "Uses graphql for entries if needed, rate-limited",
            "value": True
        },

        "stories": {
            "name": "Process stories/live videos",
            "description": "Process stories and live videos as well, requires an extra call",
            "value": True
        },

        "use_api_entries": {
            "name": "Use API entries",
            "description": "Uses API for entries if needed, rate-limited, but very fast",
            "value": False
        },

        "use_hash_graphql": {
            "name": "Use hash graphql",
            "description": "Uses query_hash instead of query_id for graphql",
            "value": True
        }
    },

    "get_url": get_url,
    "process": process
}]
