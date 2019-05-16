# -*- coding: utf-8 -*-

import time
import rssit.rest
import pprint
import re
import html
import random
import datetime
import dateutil.parser
import bs4
import sys

vod_info_cache = rssit.util.Cache("goldlive_vod_info", 24*60*60, 50)
vod_page_cache = rssit.util.Cache("goldlive_vod_page", 24*60*60, 50)

api = rssit.rest.API({
    "name": "goldlive",
    "method": "POST",
    "cookiejar": "goldlive",
    "headers": {
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "http://www.goldlive.co.kr"
    },
    "endpoints": {
        "favorite_live": {
            "url": "http://www.goldlive.co.kr/mypage/favorite_live_form",
            "form": {
                "v_type": 1,
                "u_type": "bj",
                "search_sort": "like"
            },
            "headers": {
                "Referer": "http://www.goldlive.co.kr/mypage/favorite_bj"
            }
        },
        "vod_info": {
            "url": "http://player.goldlive.co.kr/broadcast/bj_vod_more_list",
            "type": "json",
            "form": {
                "vod_key": rssit.rest.Arg("vod", 0),
                "offset": 0,
                "limit": 0,  # 3,
                "sort_type": "newest"
            },
            "headers": {
                "Referer": rssit.rest.Format("http://player.goldlive.co.kr/play/%s",
                                             rssit.rest.Arg("vod", 0)),
                "Origin": "http://player.goldlive.co.kr"
            }
        }
    }
})


def get_vod_entry(config, vodid):
    data = vod_info_cache.get(vodid)
    if not data:
        data = api.run(config, "vod_info", vodid)
        vod_info_cache.add(vodid, data)

    html_raw = data["rslt_set"]["html"]
    soup = bs4.BeautifulSoup(html_raw, 'lxml')

    info = soup.select("li.cast_infow")[0]

    caption = html.unescape(info.select("strong")[0].text)
    uid = re.sub(r".*/panbook/([0-9]*)$", "\\1", info.select("a.nick_name")[0]["href"])

    datatime_data = info.select("div.data-time > span.data")[0].text
    datatime_time = info.select("div.data-time > span.time")[0].text
    datatime = datatime_data + " " + datatime_time
    date = rssit.util.parse_date(datatime + " +0900")

    entry = {
        "caption": "[LIVE] " + caption,
        "url": "http://player.goldlive.co.kr/play/" + vodid,
        "date": date,
        "author": uid,
        "images": [],
        "videos": []
    }

    page = vod_page_cache.get(vodid)
    if not page:
        page = rssit.util.download(entry["url"], config=config)
        page = page.decode('utf-8')
        vod_page_cache.add(vodid, page)

    image = re.search(r"<meta name=\"og:image\" *content=\"(http.*?)\"", page)
    if not image:
        return entry

    image = image.group(1)

    video = re.search(r"sources:\s*[[][\s\S]*?src:\s*\"(http.*?\.m3u8)\"\s*}", page)
    #video = re.search(r"src:\s*\"(http.*?\.m3u8)\"[\s\S]*}", page)
    if not video:
        return entry

    video = video.group(1)

    entry["videos"] = [{
        "image": image,
        "video": video
    }]

    return entry


def generate_favorite_feed(server, config, path):
    # Until I find a fix
    return None

    data = api.run(config, "favorite_live").decode('utf-8')

    soup = bs4.BeautifulSoup(data, 'lxml')
    elements = soup.select("ul.list > li > span.wrap-li")

    config["is_index"] = True
    feed = {
        "title": "Favorite feed",
        "description": "Broadcasts from people you favorited",
        "url": "http://www.goldlive.co.kr/mypage/favorite_bj",
        "author": "goldlive",
        "entries": []
    }

    for element in elements:
        link = element.select("a[href='#none']")[0]
        vod = re.sub(r".*/play/([0-9]+)'[)].*", "\\1", link["onclick"])
        print(vod)
        if vod != link["onclick"]:
            entry = get_vod_entry(config, vod)
            feed["entries"].append(entry)
        else:
            sys.stderr.write("Can't parse Goldlive onclick: " + str(link["onclick"]) + "\n")

    return ("social", feed)


infos = [{
    "name": "goldlive",
    "display_name": "GoldLive",

    "endpoints": {
        "favorite_feed": {
            "name": "Favorite Feed",
            "process": generate_favorite_feed
        }
    },

    "config": {}
}]
