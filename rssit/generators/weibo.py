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
        return rssit.util.strify(element["title"])
    elif element.name == "a" and "longtext" in element.get("class", []):
        return ""
    else:
        string = ""

        for i in element.children:
            string += get_string(i)

        return string


def get_url(config, url):
    match = re.match(r"^(https?://)?weibo.wbdacdn.com/user/(?P<user>[0-9]*)", url)

    if match == None:
        match = re.match(r"^(https?://)?(www.)?weibo.com/u/(?P<user>[0-9]*)", url)

        if match == None:
            return None

    return "/u/" + match.group("user")


def generate_social_wbda(config, user):
    url = "http://weibo.wbdacdn.com/user/" + user

    data = rssit.util.download(url)

    soup = bs4.BeautifulSoup(data, 'lxml')

    username = rssit.util.strify(soup.select("h3.username")[0].text)

    descriptionel = soup.select("div.info .glyphicon-user")
    if descriptionel and len(descriptionel) > 0:
        description = rssit.util.strify(descriptionel[0].parent.text)
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

        dateels = status.select("small span a")
        if not dateels or len(dateels) <= 0:
            # invalid
            continue

        dateel = dateels[0]
        datetext = dateel["title"]

        posturl = urllib.parse.urljoin(url, rssit.util.strify(dateel["href"]))
        postid = re.search(r"\/status([0-9]+)\.html", posturl)
        if postid:
            postid = postid.group(1)

        author = rssit.util.strify(status.select(".screen_name")[0].text)

        try:
            date = parse(datetext)
        except Exception as e:
            if "小时前" in datetext:
                hoursago = int(datetext.replace("小时前", ""))
                date = datetime.datetime.now() - datetime.timedelta(hours=hoursago)
                date = date.replace(minute = 0, second = 0, microsecond = 0)
            elif "分钟前" in datetext:
                minutesago = int(datetext.replace("分钟前", ""))
                date = datetime.datetime.now() - datetime.timedelta(minutes=minutesago)
                date = date.replace(second = 0, microsecond = 0)
            else:
                print("WARNING: Unparsable date: " + datetext)
                continue

        date = rssit.util.localize_datetime(date)

        images = []

        if lotspic and len(lotspic) > 0:
            for pic in lotspic[0].select("img"):
                if pic.has_attr("data-o"):
                    images.append(re.sub(r"(//[^/]*\.cn/)[a-z]*/", "\\1large/",
                                         rssit.util.strify(pic["data-o"])))
                elif pic.has_attr("data-rel"):
                    images.append(rssit.util.strify(pic["data-rel"]))
                else:
                    images.append(re.sub(r"(//[^/]*\.cn/)[a-z]*/", "\\1large/",
                                         rssit.util.strify(pic["src"])))

        feed["entries"].append({
            "url": posturl,
            "id": postid,
            "caption": caption,
            "date": date,
            "author": author,
            "images": images,
            "videos": []
        })

    return ("social", feed)


def generate_tw(config, user):
    url = "http://tw.weibo.com/u/" + user

    data = rssit.util.download(url)

    soup = bs4.BeautifulSoup(data, 'lxml')

    username = rssit.util.strify(soup.select("#mProfile .name > h3 > a")[0].text)

    descriptionel = soup.select("#mProfile > p.intro")
    if descriptionel and len(descriptionel) > 0:
        description = rssit.util.strify(descriptionel[0].text)
    else:
        description = username + "'s weibo"

    statuses = soup.select("#weibo_container .weibo_status")

    feed = {
        "title": username,
        "author": username,
        "description": description,
        "url": url,
        "entries": {}
    }

    for status in statuses:
        """status_word = status.select("")
        if not status_word or len(status_word) < 1:
            caption = ""
        else:
            caption = get_string(status_word[0])"""

        dateels = status.select(".weibo_created_at > label")
        if not dateels or len(dateels) <= 0:
            # invalid
            continue

        dateel = dateels[0]
        datetext = dateel["data-cdt"]

        posturl = urllib.parse.urljoin(url, rssit.util.strify(status.select("p.text_link > a")[0]["href"]))
        postid = re.search(r"\/([0-9]+)[^a-zA-Z0-9/.]*$", posturl)
        if postid:
            postid = postid.group(1)

        try:
            date = parse(datetext)
        except Exception as e:
            if "小时前" in datetext:
                hoursago = int(datetext.replace("小时前", ""))
                date = datetime.datetime.now() - datetime.timedelta(hours=hoursago)
                date = date.replace(minute = 0, second = 0, microsecond = 0)
            elif "分钟前" in datetext:
                minutesago = int(datetext.replace("分钟前", ""))
                date = datetime.datetime.now() - datetime.timedelta(minutes=minutesago)
                date = date.replace(second = 0, microsecond = 0)
            else:
                print("WARNING: Unparsable date: " + datetext)
                continue

        # date = rssit.util.localize_datetime(date)

        feed["entries"][postid] = {
            "url": posturl,
            "id": postid,
            "date": date
        }

    return feed


def generate_user(config, user):
    feed = generate_social_wbda(config, user)
    otherfeed = generate_tw(config, user)

    for i in feed[1]["entries"]:
        if i["id"] in otherfeed["entries"]:
            #i["url"] = otherfeed["entries"][i["id"]]["url"]
            i["date"] = otherfeed["entries"][i["id"]]["date"]
        del i["id"]

    return feed

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
