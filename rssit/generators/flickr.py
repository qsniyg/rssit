# -*- coding: utf-8 -*-


import re
import rssit.util
import datetime
import urllib.parse
from dateutil.tz import *
import sys
import pprint


def get_modelExport(data):
    jsondatare = re.search(r"modelExport: *(?P<json>.*?), *\n", str(data))
    if jsondatare == None:
        return None

    jsondata = jsondatare.group("json")
    jsondata = rssit.util.fix_surrogates(jsondata)

    return rssit.util.json_loads(jsondata)


def get_url(config, url):
    match = re.match(r"^(https?://)?(?:\w+\.)?flickr\.com/photos/(?P<user>[^/]*)/*", url)

    if match is None:
        return None

    data = rssit.util.download(url)

    if not data:
        return None

    decoded = get_modelExport(data)

    if not decoded:
        return None

    return "/photos/" + decoded["photostream-models"][0]["owner"]["id"]


photo_size_order = ["o", "k", "h", "b", "c", "n", "m", "t", "sq", "s"]


def get_photo_url_website(sizes):
    for o in photo_size_order:
        if o in sizes:
            return sizes[o]["url"]

    return None


def get_photo_url_api(photo):
    if "originalsecret" in photo and False:
        return "https://farm%i.staticflickr.com/%s/%s_%s_o.%s" % (
            photo["farm"],
            photo["server"],
            photo["id"],
            photo["originalsecret"],
            photo["originalformat"]
        )

    for o in photo_size_order:
        key = "url_" + o

        if key in photo:
            return photo[key]

    return None


def generate_photos_url(config, user):
    url = "https://www.flickr.com/photos/" + user

    data = rssit.util.download(url)
    decoded = get_modelExport(data)

    photostream = decoded["photostream-models"][0]

    username = photostream["owner"]["username"]
    author = username

    if not config["author_username"] and "realname" in photostream["owner"]:
        if len(photostream["owner"]["realname"]) > 0:
            author = photostream["owner"]["realname"]

    feed = {
        "title": author,
        "description": "%s's flickr" % username,
        "url": url,
        "author": username,
        "social": True,
        "entries": []
    }

    photopage = photostream["photoPageList"]["_data"]
    for photo in photopage:
        if not photo:
            continue

        if "title" in photo:
            caption = photo["title"]
        else:
            caption = ""

        newcaption = str(photo["id"]) + " " + caption
        newcaption = newcaption.strip()

        date = datetime.datetime.fromtimestamp(int(photo["stats"]["datePosted"]), None).replace(tzinfo=tzlocal())

        images = [urllib.parse.urljoin(url, get_photo_url_website(photo["sizes"]))]

        if not images[0]:
            print("Skipping flickr image " + caption)
            continue

        feed["entries"].append({
            "url": "https://www.flickr.com/photos/%s/%s" % (
                user, photo["id"]
            ),
            "caption": caption,
            "media_caption": newcaption,
            "similarcaption": caption,
            "author": username,
            "date": date,
            "images": images,
            "videos": []
        })

    return feed


websiteapikey = None


def update_api_key():
    global websiteapikey
    data = rssit.util.download("https://www.flickr.com")
    match = re.search(r"^root\.YUI_config\.flickr\.api\.site_key *= *['\"]([^['\"]*)['\"] *; *$", data, re.M)
    websiteapikey = match.group(1)


def do_api_call(endpoint, *args, **kwargs):
    if "__times" in kwargs and kwargs["__times"] > 3:
        sys.stderr.write("Warning: >3 times called for flickr API\n")
        return

    if not websiteapikey:
        update_api_key()

    url = "https://api.flickr.com/services/rest?csrf=&api_key=%s&format=json&nojsoncallback=1&method=%s" % (
        websiteapikey,
        endpoint
    )

    times = 0
    if "__times" in kwargs:
        times = kwargs["__times"]
        del kwargs["__times"]

    querystring = urllib.parse.urlencode(kwargs)
    if querystring:
        url = url + "&" + querystring

    data = rssit.util.download(url)
    ret = rssit.util.json_loads(data)

    if "code" in ret and ret["code"] == 100:
        update_api_key()
        kwargs["__times"] = times + 1
        return do_api_call(endpoint, *args, **kwargs)

    return ret


def get_user_info(config, user):
    if "@N" in user:
        return do_api_call("flickr.people.getInfo", user_id=user)["person"]
    else:
        return do_api_call("flickr.people.findByUserName", username=user)["user"]


def generate_photos_api(config, user):
    userinfo = get_user_info(config, user)

    mediacount = userinfo["photos"]["count"]

    username = userinfo["username"]["_content"]
    author = username

    if not config["author_username"] and "realname" in userinfo:
        if len(userinfo["realname"]["_content"]) > 0:
            author = userinfo["realname"]["_content"]

    feed = {
        "title": author,
        "description": "%s's flickr" % username,
        "url": "https://www.flickr.com/photos/" + user,
        "author": username,
        "social": True,
        "entries": []
    }

    mediacount = 0
    if config["count"] < 0:
        mediacount = userinfo["photos"]["count"]

    count = config["count"]

    if count < 0 or count == 1:
        count = 500

    def func(page):
        if not page:
            page = 1

        photos_api = do_api_call("flickr.people.getPublicPhotos",
                                 user_id = user,
                                 safe_search = 3,
                                 per_page = count,
                                 page = 1,
                                 extras = "original_format,date_upload,url_o,url_k,url_h,url_b,url_c,url_z,url_n,url_m,url_t")["photos"]
        if not photos_api:
            return None

        photos = photos_api["photo"]

        page = page + 1

        return (photos, page, None)

    photos = rssit.util.paginate(config, mediacount, func)

    for photo in photos:
        if "title" in photo:
            caption = photo["title"]
        else:
            caption = ""

        newcaption = str(photo["id"]) + " " + caption
        newcaption = newcaption.strip()

        myentry = {
            "url": "https://www.flickr.com/photos/%s/%s" % (
                user, photo["id"]
            ),
            "caption": caption,
            "media_caption": newcaption,
            "similarcaption": caption,
            "author": username,
            "date": rssit.util.localize_datetime(datetime.datetime.fromtimestamp(int(photo["dateupload"]))),
            "images": [get_photo_url_api(photo)],
            "videos": [],
        }

        if myentry["images"][0] is None:
            sys.stderr.write("Skipping image " + photo["title"] + "\n")
            continue

        feed["entries"].append(myentry)

    return feed


def generate_photos(config, user):
    if config["prefer_api"]:
        return generate_photos_api(config, user)
    else:
        return generate_photos_url(config, user)


def process(server, config, path):
    if path.startswith("/photos/"):
        return ("social", generate_photos(config, path[len("/photos/"):]))


infos = [{
    "name": "flickr",
    "display_name": "Flickr",

    "config": {
        "author_username": {
            "name": "Author = Username",
            "description": "Set the author's name to be their username",
            "value": False
        },

        "prefer_api": {
            "name": "Prefer API over website",
            "description": "Prefers the use of the flickr API instead of scraping the website",
            "value": True
        }
    },

    "get_url": get_url,
    "process": process
}]
