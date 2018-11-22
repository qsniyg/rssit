# -*- coding: utf-8 -*-


import bs4
import urllib.request
import urllib.parse
from dateutil.parser import parse
import datetime
import rssit.util
import re
import pprint
import unicodedata
import urllib.parse


def get_string(element):
    if type(element) is bs4.element.NavigableString:
        return str(element.string)
    elif element.name == "img":
        if element.has_attr("title"):
            return rssit.util.strify(element["title"])
        else:
            return ""
    elif element.name == "a" and "longtext" in element.get("class", []):
        return ""
    elif element.name == "br":
        return "\n"
    else:
        string = ""

        for i in element.children:
            string += get_string(i)

        return string


def get_url(config, url):
    match = re.match(r"^(https?://)?weibo.wbdacdn.com/user/(?P<user>[0-9]*)", url)
    uid = None

    if match is None:
        match = re.match(r"^(https?://)?(www.)?weibo.com/u/(?P<user>[0-9]*)", url)

        if match is None:
            match = re.match(r"^(https?://)?(www.)?weibo.com/(?P<user>[^/?]*)", url)
            if match is None:
                return None
            else:
                username = match.group("user")
                uid = get_userid_for_username(config, username)
        else:
            uid = match.group("user")
    else:
        uid = match.group("user")

    if not uid:
        return None

    return "/u/" + uid


def get_max_image(url):
    return re.sub(r"(//[^/]*\.cn/)[a-z0-9]*/", "\\1large/", url)


def strip(text):
    newstr = ""

    for ch in text:
        if ch == "\n" or unicodedata.category(ch)[0] != "C":
            newstr += ch

    return newstr.strip()


def get_userid_for_username(config, username):
    url = "http://weibo.com/" + username

    data = rssit.util.download(url, config=config)
    soup = bs4.BeautifulSoup(data, 'lxml')

    for script in soup.select("script"):
        match = re.search("\$CONFIG *\[ *['\"]oid['\"] *\] *= *['\"](?P<uid>[0-9]*)['\"]", script.text)
        if not match:
            continue
        return match.group("uid")

    return None


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
            caption = strip(get_string(status_word[0]))

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


def generate_social_weibo(config, user):
    url = "http://weibo.com/u/" + user

    data = rssit.util.download(url, config=config)
    soup = bs4.BeautifulSoup(data, 'lxml')

    feed = {
        "url": url,
        "entries": []
    }

    username = None

    for script in soup.select("script"):
        jsondatare = re.search(r"^ *FM *\. *view *\( *(?P<json>{.*?}) *\);?$", script.text)
        if not jsondatare:
            continue

        jsondata = str(jsondatare.group("json"))
        decoded = rssit.util.json_loads(jsondata)

        if "html" not in decoded:
            continue

        dsoup = bs4.BeautifulSoup(decoded["html"], 'lxml')

        # Pl_Official_Headerv6__1
        if "Official_Header" in decoded["domid"]:
            username = rssit.util.strify(dsoup.select("h1.username")[0].text)
            feed["title"] = username
            feed["author"] = username

            description = rssit.util.strify(dsoup.select("div.pf_intro")[0].text).strip()
            if not description:
                description = username + "'s weibo"

            feed["description"] = description
        # Pl_Official_MyProfileFeed__21
        elif "MyProfileFeed" in decoded["domid"]:
            for status in dsoup.select(".WB_feed_type > .WB_feed_detail .WB_detail"):
                # TODO: Properly implement sharing
                newstatus = status.select(".WB_feed_expand .WB_expand")
                if newstatus and len(newstatus) > 0 and len(newstatus[0].select(".WB_info")) > 0:
                    if not config["with_reshares"]:
                        continue
                    status = newstatus[0]

                text = status.select(".WB_text")
                if not text or len(text) < 1:
                    caption = ""
                else:
                    caption = get_string(text[0])

                caption = strip(caption)

                dateel = status.findAll("a", attrs={"node-type": "feed_list_item_date"})[0]
                datetext = int(rssit.util.strify(dateel["date"]).strip())/1000
                date = rssit.util.utc_datetime(rssit.util.parse_date(datetext))

                piclistel = status.select(".media_box")
                if piclistel:
                    picsel = piclistel[0].select("li.WB_pic")
                else:
                    picsel = []
                images = []
                videos = []

                if len(picsel) > 0:
                    for pic in picsel:
                        images.append(get_max_image(urllib.parse.urljoin(url, pic.select("img")[0]["src"])))
                elif piclistel:
                    videl = piclistel[0].select("ul.WB_media_a > li")
                    if len(videl) > 0:
                        try:
                            videl = videl[0]

                            actiondata = videl.get("action-data")
                            actiondata = "&" + actiondata + "&"
                            video_src_part = re.sub(r".*&video_src=([^&]*)&.*", "\\1", actiondata)
                            if video_src_part != actiondata:
                                videosrc = "https:" + urllib.parse.unquote(video_src_part)
                                videosrc = re.sub(r"^https:https?://", "https://", videosrc)
                                # there's also:
                                # url=https://weibo.com/tv/l/QcnhER5fkh_drtI3
                                coverimg = "https:" + urllib.parse.unquote(re.sub(r".*&cover_img=([^&]*)&.*", "\\1", actiondata))
                                coverimg = get_max_image(re.sub(r"^https:https?://", "https://", coverimg))
                                videos.append({
                                    "image": coverimg,
                                    "video": videosrc
                                })
                        except Exception as e:
                            print(e)

                posturl = re.sub(r"\?[^/]*$", "", urllib.parse.urljoin(url, dateel["href"]))

                authorel = status.select(".WB_info > a.S_txt1")[0]
                if authorel.has_attr("nick-name"):
                    author = authorel["nick-name"]
                elif authorel.has_attr("title"):
                    author = authorel["title"]
                else:
                    author = authorel.text

                author = rssit.util.strify(author)

                feed["entries"].append({
                    "url": posturl,
                    "caption": caption,
                    "date": date,
                    "author": author,
                    "images": images,
                    "videos": videos
                })

    return ("social", feed)


def generate_user(config, user):
    return generate_social_weibo(config, user)

    feed = generate_social_wbda(config, user)

    try:
        otherfeed = generate_tw(config, user)

        for i in feed[1]["entries"]:
            if i["id"] in otherfeed["entries"]:
                #i["url"] = otherfeed["entries"][i["id"]]["url"]
                i["date"] = otherfeed["entries"][i["id"]]["date"]
            del i["id"]
    except Exception:
        pass

    return feed


def process(server, config, path):
    if path.startswith("/u/"):
        return generate_user(config, path[len("/u/"):])

    return None


infos = [{
    "name": "weibo",
    "display_name": "Weibo",

    "endpoints": {
        "u": {
            "name": "User's feed (by UID)",
            "process": lambda server, config, path: generate_user(config, path)
        }
    },

    "config": {
        "with_reshares": {
            "name": "Include shared weibos",
            "value": True
        }
    },

    "get_url": get_url,
    "process": process
}]
