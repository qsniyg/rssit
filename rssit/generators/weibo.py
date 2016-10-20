# -*- coding: utf-8 -*-


import bs4
import urllib.request
import urllib.parse
from dateutil.parser import parse
import datetime
import rssit.util
import re


def get_string(element):
    if type(element) is bs4.element.NavigableString:
        return str(element.string)
    elif element.name == "img":
        return element["title"]
    else:
        string = ""

        for i in element.children:
            string += get_string(i)

        return string


def get_url(url):
    match = re.match(r"^(https?://)?weibo.wbdacdn.com/user/(?P<user>[0-9]*)", url)

    if match == None:
        match = re.match(r"^(https?://)?weibo.com/u/(?P<user>[0-9]*)", url)

        if match == None:
            return None

    return "/u/" + match.group("user")


def generate_user(config, user):
    url = "http://weibo.wbdacdn.com/user/" + user

    data = rssit.util.download(url)
    #data = rssit.util.download("file:///tmp/weibo.html")

    soup = bs4.BeautifulSoup(data, 'lxml')

    username = soup.select("h3.username")[0].text

    descriptionel = soup.select("div.info .glyphicon-user")
    if descriptionel and len(descriptionel) > 0:
        description = descriptionel[0].parent.text
    else:
        description = username + "'s weibo"

    statuses = soup.select(".weibos > .status")

    feed = {
        "title": username,
        "author": username,
        "description": description,
        "url": url,
        "entries": []
    }

    for status in statuses:
        block = status.select("blockquote .status")
        if block and len(block) > 0:
            # TODO: Properly implement sharing
            status = block[0]

        lotspic = status.select(".lotspic_list")
        if not lotspic or len(lotspic) < 1:
            lotspic = status.select(".thumbs")

        status_word = status.select(".status_word")
        if not status_word or len(status_word) < 1:
            caption = ""
        else:
            caption = get_string(status_word[0])

        dateel = status.select("small span a")[0]
        datetext = dateel["title"]

        posturl = urllib.parse.urljoin(url, dateel["href"])

        author = status.select(".screen_name")[0].text

        try:
            date = parse(datetext)
        except Exception as e:
            if "小时前" in datetext:
                hoursago = int(datetext.replace("小时前", ""))
                date = datetime.datetime.now() - datetime.timedelta(hours=hoursago)
            elif "分钟前" in datetext:
                minutesago = int(datetext.replace("分钟前", ""))
                date = datetime.datetime.now() - datetime.timedelta(minutes=minutesago)
            else:
                print("WARNING: Unparsable date: " + datetext)
                continue

        date = rssit.util.localize_datetime(date)

        images = []

        if lotspic and len(lotspic) > 0:
            for pic in lotspic[0].select("img"):
                images.append(pic["data-rel"])

        feed["entries"].append({
            "url": posturl,
            "caption": caption,
            "date": date,
            "author": author,
            "images": images,
            "videos": []
        })

    return ("social", feed)

def process(server, config, path):
    if path.startswith("/u/"):
        return generate_user(config, path[len("/u/"):])

    return None


infos = [{
    "name": "weibo",
    "display_name": "Weibo",

    "config": {},

    "get_url": get_url,
    "process": process
}]
