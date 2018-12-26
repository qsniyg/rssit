# -*- coding: utf-8 -*-

import rssit.util
import rssit.rest
import pprint

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
        }
    },

    "config": {
        "api_key": {
            "name": "API Key",
            "description": "API Key",
            "value": None
        }
    }
}]
