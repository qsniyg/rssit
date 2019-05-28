# -*- coding: utf-8 -*-


import bs4
import re
import rssit.util
import pprint
import sys
from math import ceil


def generate_mariasarang_page(config, url):
    data = rssit.util.download(url)
    soup = bs4.BeautifulSoup(data, 'lxml')

    dates = soup.select("table > tr > td")
    title = None
    date = None
    if dates and len(dates) > 0:
        for date_el in dates:
            date_txt = date_el.text.strip()
            match = re.search(r"^[0-9]{4}년 [0-9]{1,2}월 [0-9]{1,2}일", date_txt)
            if match:
                title = match.group(0)
                date = rssit.util.parse_date(match.group(0))
                break

    if not date:
        sys.stderr.write("Cannot parse date\n")
        return None

    todaylecture = soup.select("div.todaylecture")
    if not todaylecture or len(todaylecture) == 0:
        sys.stderr.write("Cannot find todaylecture\n")
        return None

    text = ""

    for current_el in todaylecture[0].next_siblings:
        if current_el.name == "script":
            break

        ok = False
        if current_el.name == "h3" and current_el.has_attr("class") and "bd_tit" in current_el["class"]:
            ok = True
        elif current_el.name == "div" and current_el.has_attr("class") and "board_layout" in current_el["class"]:
            ok = True
        if not ok:
            continue
        text += "<br />\n" + str(current_el)

    return {
        "title": title,
        "url": url,
        "id": title,
        "author": "mariasarang",
        "content": text,
        "date": date
    }


def generate_mariasarang(server, config, path):
    baseurl = "https://m.mariasarang.net/page/missa.asp?go="

    feed = {
        "title": "미사 (마리아사랑)",
        "description": "오늘의 미사",
        "url": "https://m.mariasarang.net/page/missa.asp",
        "author": "mariasarang",
        "entries": []
    }

    entry = generate_mariasarang_page(config, baseurl + "0")
    if not entry:
        return None

    feed["entries"].append(entry)
    #pprint.pprint(feed)

    for i in range(ceil((config["count"] - 1) / 2)):
        entry = generate_mariasarang_page(config, baseurl + "-" + str(i + 1))
        if not entry:
            break
        feed["entries"].append(entry)
    for i in range(ceil((config["count"] - 2) / 2)):
        entry = generate_mariasarang_page(config, baseurl + str(i + 1))
        if not entry:
            break
        feed["entries"].append(entry)
    return ("feed", feed)


infos = [{
    "name": "misa",
    "display_name": "Misa",

    "endpoints": {
        "mariasarang": {
            "name": "Mariasarang",
            "process": generate_mariasarang
        }
    },

    "config": {}
}]
