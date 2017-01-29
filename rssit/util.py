# -*- coding: utf-8 -*-


import urllib.request
from dateutil.tz import *
import re
import os
import rssit.config
import rssit.http
import urllib.parse


def quote_url(link):
    link = urllib.parse.unquote(link).strip()
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(link)
    path = urllib.parse.quote(path)
    link = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))
    link = link.replace("%3A", ":")
    return link


def download(url, *args, **kwargs):
    if "config" in kwargs:
        config = kwargs["config"]
    else:
        config = {
            "timeout": 40
        }

    if "head" in kwargs and kwargs["head"]:
        request = urllib.request.Request(url, method="HEAD")
    else:
        request = urllib.request.Request(url)

    request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')
    request.add_header('Pragma', 'no-cache')
    request.add_header('Cache-Control', 'max-age=0')
    request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')

    with urllib.request.urlopen(request, timeout=config["timeout"]) as response:
        charset = response.headers.get_content_charset()

        if charset:
            return response.read().decode(charset)
        else:
            return response.read()


def convert_surrogate_pair(x, y):
    n = (((ord(x) - 0xd800 << 10) + (ord(y) - 0xdc00)) + 0x10000)
    s = "\\U%08x" % n
    return s.encode('utf-8').decode("unicode-escape")


def fix_surrogates(string):
    new_string = ""

    last_surrogate = False

    for i in range(len(string)):
        ch = string[i]
        cho = ord(ch)

        if last_surrogate:
            last_surrogate = False
            continue

        if (cho >= 0xd800 and cho <= 0xdbff) or (cho >= 0xdc00 and cho <= 0xdfff):
            new_string += convert_surrogate_pair(ch, string[i + 1])
            last_surrogate = True
        else:
            new_string += ch

    return new_string


def localize_datetime(dt):
    return dt.replace(tzinfo=tzlocal())

def utc_datetime(dt):
    return dt.replace(tzinfo=tzutc()).astimezone(tzlocal())


# http://stackoverflow.com/a/6883094
url_regex = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

def get_urls(caption):
    return re.findall(url_regex, caption)

def link_urls(caption):
    return re.sub("(" + url_regex + ")", r'<a href="\1">\1</a>', caption)


def build_all_dict(all_list, all_dict):
    for item in all_list:
        for info in item.infos:
            all_dict[info["name"]] = info


def simple_copy(data):
    if type(data) == list:
        mylist = []

        for i in data:
            mylist.append(simple_copy(i))

        return mylist
    elif type(data) == dict:
        mydict = {}

        for i in data:
            mydict[i] = simple_copy(data[i])

        return mydict
    else:
        return data


def get_host():
    core_config = rssit.config.get_section("core")

    return "http://%s:%i/" % (
        core_config["hostname"],
        rssit.http.port
    )


def get_local_url(path):
    path = os.path.normpath(path)

    return urllib.parse.urljoin(get_host(), path)
