# -*- coding: utf-8 -*-


import bs4
import sys
import urllib.request
import urllib.parse
from dateutil.parser import parse
import re
import html
import rssit.util
import demjson
import pprint


def get_url(config, url):
    match = re.match(r"^(https?://)?(?P<url>[^./]*.tistory.[a-z]*.*)", url)

    if match is None:
        match = re.match(r"^tistory:/*(https?://)?(?P<url>.*)", url)

        if match is None:
            return None

    return "/url/" + urllib.parse.quote_plus(match.group("url"))


def download(url):
    return re.sub(r"^.*?<html", "<html", rssit.util.download(url), flags=re.S)


def get_full_image(page_url, img):
    img = rssit.util.strify(img)
    if "daumcdn.net/thumb/" in img:
        img = urllib.parse.unquote(re.sub(".*fname=([^&]*).*", "\\1", img))
    return urllib.parse.urljoin(page_url, img.replace("/image/", "/original/").replace("/attach/", "/original/").replace("/media/", "/original/"))


def merge(orig, new):
    if "title" not in orig and "title" in new or True:
        orig["title"] = new["title"]

    if "author" not in orig and "author" in new or True:
        orig["author"] = new["author"]

    if "url" not in orig and "url" in new:
        orig["url"] = new["url"]

    #if "config" not in orig and "config" in new:
    #    orig["config"] = new["config"]

    if "entries" not in orig or not orig["entries"]:
        orig["entries"] = []

    index = {}

    for entry in orig["entries"]:
        index[entry["url"]] = entry

    for entry in new["entries"]:
        if entry["url"] in index:
            continue
        orig["entries"].append(entry)

    return orig


def normurl(url):
    splitted = urllib.parse.urlsplit(url)
    if re.match(r"^/[0-9]+", splitted.path):
        return splitted.scheme + "://" + splitted.netloc + "/m" + splitted.path
    return url


def get_article(article_url, article_i, total):
    article_url = normurl(article_url)

    myjson = {
        "entries": []
    }

    basetext = "(%i/%i) " % (article_i, total)
    article_i += 1

    sys.stderr.write(basetext + "Downloading %s... " % article_url)
    sys.stderr.flush()
    try:
        data = download(article_url)
    except Exception:
        sys.stderr.write("failed!\n")
        sys.stderr.flush()
        return

    sys.stderr.write("\r" + basetext + "Processing  %s... " % article_url)
    sys.stderr.flush()

    soup = bs4.BeautifulSoup(data, 'lxml')

    jsondata = soup.find(attrs={"type": "application/ld+json"}).text
    jsondecode = rssit.util.json_loads(jsondata)

    sitetitle = html.unescape(soup.find("meta", attrs={"property": "og:site_name"})["content"])
    myjson["title"] = sitetitle
    myjson["author"] = sitetitle
    author = sitetitle
    title = html.unescape(jsondecode["headline"])
    date = parse(jsondecode["datePublished"])
    album = "[" + str(date.year)[-2:] + str(date.month).zfill(2) + str(date.day).zfill(2) + "] " + title

    article_selectors = [
        ".entry .article",
        ".article_post",
        "#content",
        "#mArticle",
        "#article",
        "#entire > #contents > .post",
        "#main .article-desc",
        "section > article"
    ]

    for selector in article_selectors:
        articletag = soup.select(selector)
        if articletag and len(articletag) > 0:
            articletag = articletag[0]
            break

    if not articletag:
        sys.stderr.write("failed!\n")
        sys.stderr.flush()
        return

    images = []
    videos = []

    articlestr = str(articletag)
    re_images = re.findall("(https?://cfile\d+\.uf\.tistory\.com/(image|attach|original)/\w+)", articlestr)

    for image in re_images:
        url = get_full_image(article_url, image[0])

        if url not in images:
            images.append(url)

    lightboxes = articletag.findAll(attrs={"data-lightbox": True})


    for lightbox in lightboxes:
        image = get_full_image(article_url, lightbox["data-url"])
        if image not in images:
            images.append(image)
        #images.append(re.sub("/image/", "/original/", lightbox["data-url"]))

    #imageblocks = articletag.select(".imageblock img")
    imageblocks = articletag.select("p img, .imageblock img")

    for image in imageblocks:
        if "onclick" in image:
            url = re.sub("^open_img\(['\"](.*)['\"]\)$", "\\1", image["onclick"])

        url = image["src"]

        url = get_full_image(article_url, url)

        if url not in images:
            images.append(url)

    videotags = articletag.select("video")

    for video in videotags:
        if video.has_attr("src"):
            url = video["src"]
        else:
            sources = video.select("source")
            if len(sources) > 0:
                url = sources[0]["src"]
            else:
                continue

        videos.append({
            "image": None,
            "video": get_full_image(article_url, url)
        })

    myjson["entries"].append({
        "caption": title,
        "url": article_url,
        "album": album,
        "date": date,
        "author": author,
        "images": images,
        "videos": videos
    })

    sys.stderr.write("done\n")
    sys.stderr.flush()

    return myjson


def generate_url(config, url):
    page_url = url

    if config["force_api"]:
        retval = do_api_from_url(config, url)
        if retval != "invalid":
            return retval

    #data = re.sub(r"^.*?<html", "<html", download(url), flags=re.S)
    #data = download(url)
    #data = download("file:///tmp/tistory.html")

    #soup = bs4.BeautifulSoup(data, 'lxml')

    articles = []
    if "/tag" in url or "/search" in url or "/category" in url or url.endswith("tistory.com") or url.endswith("tistory.com/"):
        sys.stderr.write("Listing... ")
        data = download(url)
        soup = bs4.BeautifulSoup(data, 'lxml')

        parent_selectors = [
            "#searchList li a",
            ".searchList ol li a",
            ".searchList ul li a",  # qpid
            ".list_box li > a",
            "ol.article_post li a",
            "#masonry ul li.box > a",
            "#masonry li div.lbox > a",
            "#content .entry_slist ol li > a",
            "#content #content-inner .list ul li > a",
            "#result li > a",
            "ul.list_search li > a",
            "ul.list_search > li > span.list_search_cnt > a",
            ".list_wrap div.article_skin div.list_content a",
            ".gallery_ul li.grid-item > a",
            "section div.fixed_img_col ul li > a",
            "#entire > #contents > .list > ol > li > a",
            "#mArticle > .list_content > a",
            ".wrapper > #main > .row > .clearfix .grid-item > a"  # blank
        ]

        parenttag = None
        for selector in parent_selectors:
            parenttag = soup.select(selector)
            if parenttag and len(parenttag) > 0:
                #parenttag = parenttag[0]
                break

        for a in parenttag:
            article = urllib.parse.urljoin(url, a["href"])
            if article not in articles:
                articles.append(article)

        sys.stderr.write("done\n")
    else:
        articles = [url]

    myjson = {
        "title": None,
        "author": None,
        "url": page_url,
        "config": {
            "generator": "tistory"
        },
        "entries": []
    }

    total = len(articles)
    article_i = 1
    for article_url in articles:
        newjson = get_article(article_url, article_i, total)
        article_i = article_i + 1
        if newjson:
            myjson = merge(myjson, newjson)

    return ("social", myjson)


def category_to_id(base, category):
    data = rssit.util.download(base + "/m/category/" + urllib.parse.quote(category))
    soup = bs4.BeautifulSoup(data, 'lxml')

    scripts = soup.select("script")
    for script in scripts:
        if "window.TistoryList" not in script.text:
            continue

        json = demjson.decode(re.search(r"TistoryList *= *({.*})", str(script.text), re.DOTALL).group(1))
        return json["categoryId"]

    return None


def generate_api(config, base):
    url = base + "/m/data/posts.json"
    query = {
        "type": "post",
        "page": 1
    }

    if "page" in config and config["page"]:
        query["page"] = config["page"]

    if "search" in config and config["search"]:
        query["type"] = "search"
        query["keyword"] = config["search"]

    if "tag" in config and config["tag"]:
        query["type"] = "tag"
        query["categoryId"] = ""
        query["tag"] = config["tag"]

    if "categoryId" in config and config["categoryId"]:
        query["type"] = "post"
        query["categoryId"] = config["categoryId"]

    if "category" in config and config["category"]:
        query["type"] = "post"
        query["categoryId"] = category_to_id(base, config["category"])

    if "type" in config and config["type"]:
        query["type"] = config["type"]

    querystr = urllib.parse.urlencode(query)
    newurl = url + "?" + querystr

    data = rssit.util.download(newurl, httpheader_Referer=url)
    jsondata = rssit.util.json_loads(data)

    userurl = newurl
    if "origurl" in config:
        userurl = config["origurl"]

    myjson = {
        "url": userurl
    }

    total = len(jsondata["list"])
    article_i = 1
    for item in jsondata["list"]:
        #itemurl = urllib.parse.urljoin(newurl, "/m" + urllib.parse.urlsplit(item["url"]).path)
        itemurl = normurl(urllib.parse.urljoin(newurl, item["url"]))
        newjson = get_article(itemurl, article_i, total)
        article_i = article_i + 1
        if newjson:
            myjson = merge(myjson, newjson)

    return ("social", myjson)


def do_api_from_url(config, url):
    if "/tag" in url or "/search" in url or "/category" in url or url.endswith("tistory.com") or url.endswith("tistory.com/"):
        split = urllib.parse.urlsplit(url)
        base = split.scheme + "://" + split.netloc
        config["origurl"] = url
        url = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
        if "/tag/" in url:
            splitted = url.split("/tag/")[1]
            if splitted:
                config["tag"] = splitted

        if "/category/" in url:
            splitted = url.split("/category/")[1]
            if splitted:
                config["category"] = splitted

        if "/search/" in url:
            splitted = url.split("/search/")[1]
            if splitted:
                config["search"] = splitted

        return generate_api(config, base)
    return "invalid"


def process(server, config, path):
    if path.startswith("/url/"):
        path = re.sub(".*?/tistory", "", config["fullpath"])
        url = "http://" + path[len("/url/"):]
        return generate_url(config, url)

    if path.startswith("/api/"):
        #path = re.sub(".*?/tistory", "", config["fullpath"])
        url = "http://" + path[len("/api/"):]
        return generate_api(config, url)

    return None


infos = [{
    "name": "tistory",
    "display_name": "Tistory",

    "endpoints": {
        "url": {
            "name": "URL",
            "process": lambda server, config, path: generate_url(config, rssit.util.addhttp(urllib.parse.unquote_plus(path)))
        },

        "api": {
            "name": "Mobile API",
            "process": lambda server, config, path: generate_api(config, rssit.util.addhttp(urllib.parse.unquote_plus(path)))
        }
    },

    "config": {
        "force_api": {
            "name": "Force API",
            "description": "Forces usage of the mobile API (works most reliably)",
            "value": True
        }
    },

    "get_url": get_url,
    "process": process
}]
