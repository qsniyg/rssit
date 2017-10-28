# -*- coding: utf-8 -*-


import urllib.request
from dateutil.tz import *
from tzlocal import get_localzone
import pytz
import datetime
from dateutil.parser import parse
import re
import os
import rssit.config
import rssit.http
import urllib.parse
import sys
import pprint
import http.cookiejar


instagram_ua = "Instagram 10.26.0 (iPhone7,2; iOS 10_1_1; en_US; en-US; scale=2.00; gamut=normal; 750x1334) AppleWebKit/420+"


def quote_url(link):
    link = urllib.parse.unquote(link).strip()
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(link)
    path = urllib.parse.quote(path)
    link = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))
    link = link.replace("%3A", ":")
    return link


def quote_url1(link):
    return urllib.parse.quote(link, safe="%/:=&?~#+!$,;'@()*[]")


def download(url, *args, **kwargs):
    if "config" in kwargs:
        config = kwargs["config"]
    else:
        config = {
            "timeout": 40
        }

    if "head" in kwargs and kwargs["head"]:
        request = urllib.request.Request(url, method="HEAD")
    elif "post" in kwargs and kwargs["post"]:
        request = urllib.request.Request(url, data=kwargs["post"], method="POST")
    else:
        request = urllib.request.Request(url)

    if "http_noextra" not in kwargs:
        request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')
        request.add_header('Pragma', 'no-cache')
        request.add_header('Cache-Control', 'max-age=0')
        request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')

    httpheaders = {}
    for key in config:
        if key.startswith("httpheader_"):
            httpheaders[key] = config[key]

    for key in kwargs:
        if key.startswith("httpheader_"):
            httpheaders[key] = kwargs[key]

    for key in httpheaders:
        if key.startswith("httpheader_"):
            headername = list(key[len("httpheader_"):])

            shouldupper = True
            for i in range(len(headername)):
                if headername[i].islower() and shouldupper:
                    headername[i] = headername[i].upper()
                    shouldupper = False
                if headername[i] == '-':
                    shouldupper = True

            headername = "".join(headername)

            request.add_header(headername, httpheaders[key])

    if "proxy" in config and config["proxy"]:
        proxy_support = urllib.request.ProxyHandler({"http": config["proxy"]})
        opener = urllib.request.build_opener(proxy_support)
        openf = opener.open
    else:
        openf = urllib.request.urlopen

    with openf(request, timeout=config["timeout"]) as response:
        charset = response.headers.get_content_charset()

        ourresponse = response.read()

        if charset:
            try:
                return ourresponse.decode(charset)
            except Exception as e:
                sys.stderr.write("Error decoding charset " + charset + ": " + str(e) + "\n")
                return ourresponse

        return ourresponse


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


# https://stackoverflow.com/q/27531718
def good_timezone_converter(input_dt, current_tz='UTC', target_tz='US/Eastern'):
    current_tz = pytz.timezone(current_tz)
    target_tz = get_localzone()  #pytz.timezone(target_tz)
    target_dt = current_tz.localize(input_dt).astimezone(target_tz)
    return target_tz.normalize(target_dt)


def need_timezone(dt):
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None

def localize_datetime(dt):
    if need_timezone(dt):
        return dt.replace(tzinfo=tzlocal())
    else:
        return dt.astimezone(get_localzone())

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


def ascii_only(string):
    return ''.join([i if ord(i) < 128 else ' ' for i in string])


def parse_date(date):
    if type(date) in [int, float]:
        return rssit.util.localize_datetime(datetime.datetime.utcfromtimestamp(date))
    date = date.strip()
    date = re.sub("^([0-9][0-9][0-9][0-9])\. ([0-9][0-9])\.([0-9][0-9])[(].[)]", "\\1-\\2-\\3 ", date) # tvdaily
    date = re.sub("오후 *([0-9]*:[0-9]*)", "\\1PM", date)
    date = re.sub("(^|[^0-9])([0-9][0-9])\.([0-9][0-9])\.([0-9][0-9])  *([0-9][0-9]:[0-9][0-9])",
                  "\\1 20\\2-\\3-\\4 \\5", date) # mbn
    date = date.replace("\n", "   ")  # fnnews
    if "수정시간" in date:
        date = re.sub(".*수정시간", "", date)
    if "수정 :" in date:
        date = re.sub(".*수정 :", "", date)
    if "기사수정" in date: # xportsnews
        date = re.sub(".*기사수정", "", date)
    date = re.sub(" 송고.*", "", date) # news1
    date = re.sub("[(]월[)]", "", date) # chicnews
    date = re.sub("SBS *[A-Z]*", "", date) # sbs
    #print(date)
    #date = re.sub("입력: *(.*?) *\| *수정.*", "\\1", date) # chosun
    #print(date)
    date = re.sub(r"([0-9]*)년 *([0-9]*)월 *([0-9]*)일 *([0-9]*):([0-9]*)[PA]M", "\\1-\\2-\\3 \\4:\\5", date)  # inews24
    date = date.replace("년", "-")
    date = date.replace("年", "-")
    date = date.replace("월", "-")
    date = date.replace("月", "-")
    date = date.replace("日", "")
    date = date.replace("시", ":")
    date = ascii_only(date)
    date = re.sub("\( *\)", "", date)
    date = re.sub("\( *= *1 *\)", "", date) # workaround for news1
    date = re.sub("\( *= *1Biz *\)", "", date) # workaround for news1
    date = re.sub("\|", " ", date)
    date = re.sub(":[^0-9]*$", "", date)
    while re.search("^[^0-9]*[:.].*", date):
        date = re.sub("^[^0-9]*[:.]", "", date)
    date = date.strip()
    date = re.sub("^([0-9][0-9][0-9][0-9])\. ([0-9][0-9])\.([0-9][0-9])$", "\\1-\\2-\\3", date) #tvdaily
    #print(date)
    #print(parse(date))
    if not date:
        return None
    return rssit.util.localize_datetime(parse(date))


def get_selector(soup, selectors):
    tag = None

    data = None
    for selector in selectors:
        if type(selector) in [list, tuple]:
            data = selector[1]
            selector = selector[0]
        else:
            data = None

        tag = soup.select(selector)
        if tag and len(tag) > 0:
            #print(selector)
            break
        else:
            tag = None

    if data:
        return (tag, data)

    return tag
