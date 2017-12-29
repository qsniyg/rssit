# -*- coding: utf-8 -*-


import bs4
import sys
import urllib.request
import urllib.parse
from dateutil.parser import parse
import re
import html
import pprint
import rssit.util
import demjson


def get_url(config, url):
    match = re.match(r"^(https?://)?(?P<url>blog.naver.com.*)", url)

    if match is None:
        match = re.match(r"^naverblog:/*(https?://)?(?P<url>.*)", url)

        if match is None:
            return None

    return "/url/" + urllib.parse.quote_plus(match.group("url"))


def generate_url(config, url):
    #url = rssit.util.quote_url(url)
    url = rssit.util.addhttp(urllib.parse.unquote_plus(url))

    data = rssit.util.download(url)

    soup = bs4.BeautifulSoup(data, 'lxml')

    scripts = soup.select("script")
    blogid = ""
    for script in scripts:
        match = re.search(r"var  *blogId *= *(?P<blogid>'[^']*') *", script.text)
        if match is None:
            continue
        blogid = demjson.decode(match.group("blogid"))

    if not blogid:
        sys.stderr.write("no blogid\n")
        return

    myjson = {
        "title": blogid,
        "author": blogid,
        "url": url,
        "config": {
            "generator": "tumblr"
        },
        "entries": []
    }

    urls = [None]

    def do_urls(selector):
        urls = []
        items = soup.select(selector)
        for item in items:
            newurl = urllib.parse.urljoin(url, item["href"])
            if newurl not in urls:
                urls.append(newurl)
        return urls

    if "PrologueList.nhn" in url:
        urls = do_urls("#prologue p.p_img > a")

    if "PostThumbnailList.nhn" in url:
        urls = do_urls("#PostThumbnailAlbumViewArea p.list_image > a")

    if "PostListByTagName.nhn" in url:
        urls = do_urls("#tag_list td .image > a")

    i = 0
    for url in urls:
        if url:
            sys.stderr.write("\r[%i/%i] Downloading %s... " %
                             (i+1, len(urls), url))
            i = i + 1
            data = rssit.util.download(url)
            soup = bs4.BeautifulSoup(data, 'lxml')

            frames = soup.select("frame#mainFrame")
            if frames:
                data = rssit.util.download(urllib.parse.urljoin(url, frames[0]["src"]))
                soup = bs4.BeautifulSoup(data, 'lxml')

            sys.stderr.write("done\n")

        author = blogid

        date = rssit.util.parse_date(soup.select("._postAddDate")[0].text)

        scripts = soup.select("script")
        title = ""
        for script in scripts:
            match = re.search(r"title *: *(?P<title>\"[^\"]*\") *,", script.text)
            if match is None:
                continue
            title = demjson.decode(match.group("title"))

        if not title:
            sys.stderr.write("no title\n")
            continue

        images = []

        for script in scripts:
            match = re.search(r"aPostImageFileSizeInfo[[][0-9]*[]] * = *(?P<json>{.*?});", script.text)
            if match is None:
                continue
            jsondata = match.group("json")
            jsonparse = demjson.decode(jsondata)
            for image in jsonparse:
                images.append(urllib.parse.urljoin("http://blogfiles.naver.net", image))

        # TODO: description, post images
        album = "[" + str(date.year)[-2:] + str(date.month).zfill(2) + str(date.day).zfill(2) + "] " + title

        myjson["entries"].append({
            "caption": title,
            "url": url,
            "album": album,
            "date": date,
            "author": author,
            "images": images,
            "videos": []
        })

    return ("social", myjson)


def process(server, config, path):
    if path.startswith("/url/"):
        #url = "http://" + path[len("/url/"):]
        url = "http://" + re.sub(".*?/url/", "", config["fullpath"])
        return generate_url(config, url)

    return None


infos = [{
    "name": "naverblog",
    "display_name": "Naver Blog",

    "endpoints": {
        "url": {
            "name": "URL",
            "process": lambda server, config, path: generate_url(config, path)
        }
    },

    "config": {},

    "get_url": get_url,
    "process": process
}]
