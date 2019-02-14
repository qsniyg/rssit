# -*- coding: utf-8 -*-

import rssit.util
import rssit.rest
import pprint
import re

video_cache = rssit.util.Cache("yt_video", 24*60*60, 50)

api = rssit.rest.API({
    "name": "youtube",
    "type": "json",
    "http_noextra": True,
    "endpoints": {
        "channel": {
            "url": "https://www.googleapis.com/youtube/v3/search",
            "query": {
                "key": rssit.rest.Arg("key", 10),
                "channelId": rssit.rest.Arg("channel", 0),
                "part": "id,snippet",
                "order": "date",
                "maxResults": rssit.rest.Arg("count", 1)
            }
        },
        "playlist": {
            "url": "https://www.googleapis.com/youtube/v3/playlistItems",
            "query": {
                "key": rssit.rest.Arg("key", 10),
                "playlistId": rssit.rest.Arg("playlist", 0),
                "part": "snippet,contentDetails",
                "maxResults": rssit.rest.Arg("count", 1)
            }
        },
        "video": {
            "url": "https://www.googleapis.com/youtube/v3/videos",
            "query": {
                "key": rssit.rest.Arg("key", 10),
                "id": rssit.rest.Arg("video", 0),
                "part": "snippet"
            }
        }
    }
})


def get_youtube_url(vidid):
    return "https://youtu.be/" + vidid


def get_video_entry(video, url):
    created = rssit.util.parse_date(video["snippet"]["publishedAt"])

    selected_thumbnail = None
    largest = 0

    if "thumbnails" in video["snippet"]:
        for thumbnail_key in video["snippet"]["thumbnails"]:
            thumbnail = video["snippet"]["thumbnails"][thumbnail_key]
            current = thumbnail["width"] * thumbnail["height"]
            if current > largest:
                selected_thumbnail = thumbnail
                largest = current

    newvideo = {
        "video": url
    }

    if selected_thumbnail is not None:
        newvideo["image"] = selected_thumbnail["url"]

    entry = {
        "url": url,
        "caption": video["snippet"]["title"],
        "description": video["snippet"]["description"],
        "date": created,
        "author": video["snippet"]["channelTitle"],
        "images": [],
        "videos": [newvideo]
    }

    return entry


def generate_channel(server, config, path):
    channel = path

    count = config["count"]
    if count == 1:
        count = 25

    response = api.run(config, "channel", channel, count, key=config["api_key"])
    #pprint.pprint(response)
    items = response["items"]
    firstitem = items[0]

    channeltitle = firstitem["snippet"]["channelTitle"]

    feed = {
        "title": channeltitle,
        "author": channeltitle,
        #"description":
        "url": "https://youtube.com/channel/" + channel,
        "config": {
            "generator": "youtube"
        },
        "entries": []
    }

    for item in items:
        vidid = item["id"]["videoId"]
        url = "https://youtu.be/" + vidid

        video = video_cache.get(vidid)
        if not video:
            video = api.run(config, "video", item["id"]["videoId"], key=config["api_key"])["items"][0]
            video_cache.add(vidid, video)

        entry = get_video_entry(video, url)

        feed["entries"].append(entry)

    return ("social", feed)


def generate_playlist(server, config, path):
    playlist = path

    count = config["count"]
    if count == 1:
        count = 25

    response = api.run(config, "playlist", playlist, count, key=config["api_key"])
    #pprint.pprint(response)
    items = response["items"]
    firstitem = items[0]

    channeltitle = firstitem["snippet"]["channelTitle"]
    channel = firstitem["snippet"]["channelId"]

    feed = {
        "title": channeltitle,
        "author": channeltitle,
        #"description":
        "url": "https://youtube.com/channel/" + channel,
        "config": {
            "generator": "youtube"
        },
        "entries": []
    }

    for item in items:
        vidid = item["contentDetails"]["videoId"]
        url = "https://youtu.be/" + vidid

        entry = get_video_entry(item, url)

        feed["entries"].append(entry)

    return ("social", feed)


def request_youtube_webpage(config, path):
    kwargs = {
        "config": config,
        "httpheader_Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "httpheader_Accept-Encoding": "gzip, deflate",
        "httpheader_Accept-Language": "en",
        "httpheader_Cache-Control": "max-age=0",
        "httpheader_Sec-Metadata": "cause=forced, destination=document, target=top-level, site=cross-site",
        "http_noextra": True
    }
    return rssit.util.download(path, **kwargs).decode("utf-8")


def request_youtube_json(config, path, regex):
    youtubepage = request_youtube_webpage(config, path + "?disable_polymer=0")
    #print(youtubepage)
    jsondata = re.search(regex, youtubepage)
    if not jsondata:
        return None

    json = rssit.util.json_loads(jsondata.group("json"))
    return json


def get_channel_json(config, path):
    #print(path)
    #regex = r"window[[]['\"]ytInitialData['\"][]] = (?P<json>{.*?});\s+(?:window[[]|if [(])"
    regex = r"window[[]['\"]ytInitialData['\"]] = (?P<json>{.*?});"
    return request_youtube_json(config, path, regex)


def get_channel_live(config, channelid):
    json = get_channel_json(config, "https://www.youtube.com/channel/" + channelid)
    #json = request_youtube_json(config, "https://www.youtube.com/channel/" + channelid, r"window[[]['\"]ytInitialData['\"]] = (?P<json>{.*?});\s+window[[]")
    channelid = json["metadata"]["channelMetadataRenderer"]["externalId"]
    tabs = json["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
    for tab in tabs:
        if "tabRenderer" not in tab:
            continue

        tab = tab["tabRenderer"]
        if "content" not in tab or "sectionListRenderer" not in tab["content"]:
            continue
        slist = tab["content"]["sectionListRenderer"]["contents"]
        for item in slist:
            if "itemSectionRenderer" not in item:
                continue
            item = item["itemSectionRenderer"]["contents"]
            for renderer_wrapper in item:
                for renderer_key in renderer_wrapper:
                    renderer = renderer_wrapper[renderer_key]
                    if "items" not in renderer:
                        continue
                    items = renderer["items"]
                    for subitem in items:
                        if "videoRenderer" not in subitem:
                            continue
                        vrenderer = subitem["videoRenderer"]
                        if ("badges" not in vrenderer or
                            len(vrenderer["badges"]) == 0 or
                            "metadataBadgeRenderer" not in vrenderer["badges"][0] or
                            vrenderer["badges"][0]["metadataBadgeRenderer"]["style"] != "BADGE_STYLE_TYPE_LIVE_NOW"):
                            continue

                        vidid = vrenderer["videoId"]
                        video = video_cache.get(vidid)
                        if not video:
                            video = api.run(config, "video", vidid, key=config["api_key"])["items"][0]
                            video_cache.add(vidid, video)
                        entry = get_video_entry(video, get_youtube_url(vidid))
                        entry["caption"] = "[LIVE] " + entry["caption"]
                        entry["author"] = channelid
                        return entry


def generate_lives(server, config, path):
    json = request_youtube_json(config, "https://www.youtube.com/", r"var ytInitialGuideData = (?P<json>{.*?});\s+if")
    items = json["items"]
    lives = []
    for item in items:
        if "guideSubscriptionsSectionRenderer" not in item:
            continue

        subs = item["guideSubscriptionsSectionRenderer"]
        for item in subs["items"]:
            if "guideEntryRenderer" not in item:
                continue
            entry = item["guideEntryRenderer"]
            if "badges" not in entry:
                continue
            if "liveBroadcasting" not in entry["badges"] or entry["badges"]["liveBroadcasting"] is not True:
                continue
            channelid = entry["entryData"]["guideEntryData"]["guideEntryId"]
            lives.append(channelid)
        break

    feed = {
        "title": "Livestreams",
        "author": "youtube",
        "url": "https://www.youtube.com/live",
        "config": {
            "generator": "youtube"
        },
        "entries": []
    }

    for live in lives:
        feed["entries"].append(get_channel_live(config, live))

    return ("social", feed)


def get_url(config, url):
    match = re.match(r"^(https?://)?(?:\w+\.)?youtube\.com/user/(?P<user>[^/]*)", url)

    if match is None:
        return

    return "/channel/" + get_channel_json(config, url)["metadata"]["channelMetadataRenderer"]["externalId"]


infos = [{
    "name": "youtube",
    "display_name": "Youtube",

    "endpoints": {
        "channel": {
            "name": "Channel",
            "process": generate_channel
        },
        "playlist": {
            "name": "Playlist",
            "process": generate_playlist
        },
        "lives": {
            "name": "Livestreams",
            "process": generate_lives
        }
    },

    "config": {
        "api_key": {
            "name": "API Key",
            "description": "API Key",
            "value": None
        }
    },

    "get_url": get_url
}]
