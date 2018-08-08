# -*- coding: utf-8 -*-

import time
import rssit.rest
import pprint
import re

# iPad API:
# https://proxsee.pscp.tv/api/v2/
# every call has ?build=... at the end
# uid = periscope uid, string of sorts, not the username
# headers:
#   User-Agent: ...
#   Accept: */*
#   Locale: ko
#   Accept-Language: ko-KR;q=1
#   Content-Type: application/json -- for post
#   X-Idempotence: unix timestamp with millis
#   Connection: keep-alive
#   Build: ...
#   Cookie: sid=...; uid=...
#   X-Attempt: 1
#   Proxy-Connection: keep-alive
#   Accept-Encoding: gzip, deflate
#
# POST loginTwitter
#   JSON: {
#     bundle_id: "com.bountylabs.periscope",
#    "create_user": false,
#    "periscope_id": ...,
#    "session_key": ...,
#    "session_secret": ...,
#    "time_zone": ...,
#    "vendor_id": ... (GUID-like string)
#   }
#   returns JSON: {
#     cookie: "..." # different cookie, but it's not used in future calls?
#     settings: {...}
#     suggested_username: "",
#     user: {...}
#   }
# POST user
#   JSON: {
#     cookie: ... # sid
#     user_id: ... # uid
#   }
# POST authorizeToken
#   JSON: {
#     cookie: ... # sid
#     service: "notification"
#   }
#   returns JSON: {
#     "authorization_token": "..."
#   }
# POST getAssociatedAccounts
#   JSON: {
#     cookie: ... # sid
#   }
# POST registerToken
#   JSON: {
#      build: ...
#      bundle_id: "com.bountylabs.periscope",
#      cookie: sid,
#      device_type: "iPad",
#      locale: "ko",
#      model: ...,
#      os: ...,
#      token: long hex string,
#      vendor_id: ...,
#   }
# POST followingBroadcastFeed
#   JSON: {
#     cookie: ...
#   }
#   returns JSON: [
#     {
#       many fields
#       state: "RUNNING"|"TIMED_OUT"|"ENDED" (many earlier ones say "TIMED_OUT" instead of "ENDED"),
#       created_at/end/ping/start/updated_at/watched_time/timedout: timestamp ending with Z
#       created_at != start
#       timedout only exists in TIMED_OUT states
#       end only exists in ENDED states
#       status: text (caption?)
#       expiration: -1,
#       id: unique id
#     }
#   ]
# POST accessVideo
#  JSON: {
#    broadcast_id: ...,
#    cookie: sid,
#    from_push: false
#  }
#  returns JSON: {
#    autoplay_view_threshold: 3
#    broadcast: {...}
#    chat_token: ...
#    default_playback_buffer_length: 1,
#    hls_is_encrypted: false,
#    hls_url: ...,
#    https_hls_url: ..., # same as hls_url?
#    is_super_resolution_eligible: false,
#    lhls_is_encrypted: ..., #lowlatencylong.m3u8
#    lhlsweb_url: ..., #lhlsweb.m3u8
#    replay_url: ..., # only available on replays
#    life_cycle_token: ...,
#    max_playback_buffer_length: 10,
#    min_playback_buffer_length: 2,
#    session: "",
#    share_url: ...,
#    type: "StreamTypeLowLatency"
#  }

# Browser API:
# base: https://api.periscope.tv/api/v2/
# headers:
#   X-Attempt: 1
#   X-Idempotence: timestamp--guid
#   X-Periscope-User-Agent: PeriscopeWeb/App (7c8c03d2192bd2bc0a4eb940f6135ab0451e8215) Chrome/version (os;arch)
#
# GET getBroadcastPublic
#   broadcast_id=...
# POST accessVideo
#  headers:
#   X-Periscope-Csrf: Periscope
#  JSON: {
#    broadcast_id: ...,
#    replay_redirect: false
#  }


def before_request(config, baseurl):
    config["httpheader_X-Idempotence"] = int(round(time.time() * 1000))


api = rssit.rest.API({
    "type": "json",
    "headers": {
        "User-Agent": rssit.rest.Arg("useragent", 12),
        "Accept": "*/*",
        "Locale": "ko",
        "Accept-Language": "ko-KR;q=1",
        "Connection": "keep-alive",
        "Build": rssit.rest.Arg("build_header", 13),
        "Cookie": rssit.rest.Arg("cookie", 10),
        "X-Attempt": "1",
        "Proxy-Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate"
    },
    "query": {
        "build": rssit.rest.Arg("build", 14)
    },
    "method": "POST",
    "form_encoding": "json",
    "pre": before_request,
    "http_noextra": True,
    "endpoints": {
        "following_feed": {
            "url": "https://proxsee.pscp.tv/api/v2/followingBroadcastFeed",
            "form": {
                "cookie": rssit.rest.Arg("sid", 11)
            }
        },
        "video": {
            "url": "https://proxsee.pscp.tv/api/v2/accessVideo",
            "form": {
                "broadcast_id": rssit.rest.Arg("id", 0),
                "cookie": rssit.rest.Arg("sid", 11),
                "from_push": False
            }
        }
    }
})


def get_cookie(config):
    return "sid=" + config["sid_cookie"] + "; uid=" + config["uid"]


def run_api(config, *args, **kwargs):
    newkwargs = rssit.util.simple_copy(kwargs)
    newkwargs["cookie"] = get_cookie(config)
    newkwargs["sid"] = config["sid_cookie"]
    newkwargs["build"] = config["build"]
    newkwargs["build_header"] = config["build_header"]
    newkwargs["useragent"] = config["useragent"]
    return api.run(config, *args, **newkwargs)


def generate_following_feed(server, config, path):
    response = run_api(config, "following_feed")

    config["is_index"] = True
    feed = {
        "title": "Following feed",
        "description": "Streams from people you follow",
        "url": "https://www.periscope.tv/?following=true", # fake url for now
        "author": "periscope",
        "entries": []
    }

    for item in response:
        state = item["state"]
        caption = "[LIVE]"
        replay = False
        if state == "ENDED" or state == "TIMED_OUT":
            caption = "[LIVE REPLAY]"
            replay = True

        url = "https://www.periscope.tv/" + item["username"] + "/" + item["id"]

        entry = {
            "caption": caption,
            "url": url,
            "author": item["username"],
            "date": rssit.util.parse_date(item["created_at"]),
            "images": [],
            "videos": [{
                #"image": item["image_url"],
                "video": rssit.util.get_local_url("/f/periscope/video/" + item["id"] + ".m3u8"),
                "headers": {
                    "User-Agent": config["streamuseragent"]
                }
            }]
        }

        if not replay: # youtube-dl should be able to support hls
            entry["videos"][0]["live_streamlink"] = True

        feed["entries"].append(entry)
    return ("social", feed)
    #return ("raw", pprint.pformat(response).encode('utf-8'))


def generate_video(server, config, path):
    response = run_api(config, "video", re.sub(r"\.[a-z0-9]+$", "", path))

    video_url = None
    preference = [
        "replay_url",
        "https_hls_url",
        "hls_url",
        # low latency later, unless that means a quality decrease
        "lhls_url",
        "lhlsweb_url",
    ]

    for pref in preference:
        if pref in response and response[pref]:
            video_url = response[pref]
            break

    if video_url:
        server.send_response(301, "Moved")
        server.send_header("Location", video_url)
        server.end_headers()

        return True
    return ("raw", pprint.pformat(response).encode('utf-8'))


infos = [{
    "name": "periscope",
    "display_name": "Periscope",

    "endpoints": {
        "following_feed": {
            "name": "Following Feed",
            "process": generate_following_feed
        },
        "video": {
            "name": "Video",
            "process": generate_video
        }
    },

    "config": {
        "sid_cookie": {
            "name": "SID Cookie",
            "value": None
        },
        "uid": {
            "name": "UID",
            "value": None
        },
        "build": {
            "name": "'build' query string",
            "value": None
        },
        "build_header": {
            "name": "'Build' header",
            "value": None
        },
        "useragent": {
            "name": "App user agent",
            "value": None
        },
        "streamuseragent": {
            "name": "Stream user agent",
            "value": None
        }
    }
}]
