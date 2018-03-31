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
import json
import random
import sortedcontainers
import collections
try:
    import redis
except ImportError:
    redis = None

rinstance = None
try:
    rinstance = redis.StrictRedis(host='localhost', db=1, charset="utf-8", decode_responses=True)
except:
    rinstance = None

try:
    try:
        from gi.repository import GObject as gobject
        from gi.repository import GLib as glib
    except ImportError:
        import gobject
except ImportError:
    gobject = None


instagram_ua = "Instagram 10.26.0 (iPhone7,2; iOS 10_1_1; en_US; en-US; scale=2.00; gamut=normal; 750x1334) AppleWebKit/420+"

user_agents = [
    'Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36',

    # from http://useragentstring.com
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
    'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16',

    # from https://techblog.willshouse.com/2012/01/03/most-common-user-agents/
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Safari/604.1.38',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36 OPR/48.0.2685.52'
]


def get_random_user_agent():
    return random.choice(user_agents)


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

    config["http_error"] = 500

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

    finished = False
    times = 0
    ourresponse = b''
    content_length = -1
    while not finished:
        times = times + 1
        if times > 3:
            finished = True

        if content_length > 0:
            request.add_header('Range', 'bytes=%i-%i' % (len(ourresponse), content_length))

        try:
            with openf(request, timeout=config["timeout"]) as response:
                for header in response.headers._headers:
                    if header[0].lower() == "content-length":
                        content_length = int(header[1])

                charset = response.headers.get_content_charset()

                try:
                    ourresponse += response.read()
                    finished = True
                except http.client.IncompleteRead as e:
                    ourresponse += e.partial

                config["http_error"] = 200

                if charset:
                    try:
                        return ourresponse.decode(charset)
                    except Exception as e:
                        sys.stderr.write("Error decoding charset " + charset + ": " + str(e) + "\n")
                        return ourresponse

                return ourresponse
        except urllib.error.HTTPError as e:
            if e.code == 302:
                # infinite loop
                config["http_error"] = 500
            else:
                config["http_error"] = e.code

            if e.code == 404 or e.code == 403 or e.code == 410:  # 410: instagram
                raise e


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


def paginate(config, mediacount, f):
        total = config["count"]
        if config["count"] == -1:
            total = mediacount

        maxid = None
        nodes = []
        console = False
        has_next_page = True

        while (len(nodes) < total) and (has_next_page is not False):
            output = f(maxid)
            if not output or not output[0]:
                break

            nodes.extend(output[0])
            if len(nodes) < total:
                sys.stderr.write("\rLoading media (%i/%i)... " % (len(nodes), total))
                sys.stderr.flush()
                console = True
            maxid = output[1]
            has_next_page = output[2]

        if console:
            sys.stderr.write("\n")
            sys.stderr.flush()

        return nodes


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


def htmlify(text):
    return rssit.util.link_urls(text).replace("\n", "<br />\n")


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
    elif type(data) in [dict, collections.OrderedDict]:
        if type(data) == collections.OrderedDict:
            mydict = collections.OrderedDict()
        else:
            mydict = {}

        for i in data:
            mydict[i] = simple_copy(data[i])

        return mydict
    else:
        return data


def simplify_copy(data):
    if type(data) == list:
        mylist = []

        for i in data:
            mylist.append(simplify_copy(i))

        return mylist
    elif type(data) == dict:
        mydict = {}

        for i in data:
            mydict[i] = simplify_copy(data[i])

        return mydict
    elif type(data) == bytes:
        return str(data)
    elif type(data) == datetime.datetime:
        return int(data.timestamp())
    else:
        return data


def get_host():
    core_config = rssit.config.get_section("core")

    return "http://%s:%i/" % (
        core_config["hostname"],
        rssit.http.port
    )


def get_local_url(path, *args, **kwargs):
    if "norm" not in kwargs or kwargs["norm"]:
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


def json_loads(x):
    return json.loads(x)

def json_dumps(x):
    return json.dumps(x)


def strify(x):
    if type(x) is list:
        nx = []
        for i in x:
            nx.append(strify(i))
        return nx
    if type(x) is dict:
        nx = {}
        for i in x:
            nx[strify(i)] = strify(x[i])
    if type(x) in [float, int]:
        return x
    elif x:
        return str(x)
    else:
        return x


class Cache():
    def __init__(self, name, timeout, rand=0):
        self.db = {}
        self.name = name
        self.timestamps = sortedcontainers.SortedDict()
        self.timeout = timeout
        self.rand = rand

    def now(self):
        return int(datetime.datetime.now().timestamp())

    def get_redis_key(self, key):
        return "RSSIT:" + str(self.name) + ":" + str(key)

    def add(self, key, value):
        if key in self.db:
            timestamp = self.db[key]["timestamp"]
            if timestamp in self.timestamps:
                del self.timestamps[timestamp]

        self.collect()

        now = self.now()
        self.timestamps[now] = key
        self.db[key] = {
            "value": value,
            "timestamp": now
        }

        if rinstance:
            rinstance.setex(self.get_redis_key(key), self.timeout, json_dumps(value))

    def get(self, key):
        self.collect()

        if self.rand > 0 and random.randint(0, self.rand) == 0:
            return None

        if rinstance:
            val = rinstance.get(self.get_redis_key(key))
            if not val:
                return None
            else:
                return json_loads(val)

        if key not in self.db:
            return None

        return self.db[key]["value"]

    def get_all(self):
        # FIXME: somehow work with redis?
        newdb = {}

        for key in self.db:
            newdb[key] = self.db[key]["value"]

        self.collect()

        return newdb

    def collect(self):
        now = self.now()
        time_id = self.timestamps.bisect_left(now - self.timeout)

        if time_id > 0:
            for i in reversed(range(0, time_id)):
                timestamp = self.timestamps.iloc[i]
                if timestamp not in self.timestamps:
                    continue
                key = self.timestamps[timestamp]
                del self.db[key]
                del self.timestamps[timestamp]


def addhttp(url):
    if not re.search("^[^/]+://", url):
        return "http://" + url
    return url


class HTTPErrorException(BaseException):
    def __init__(self, exception, traceback, code):
        self.exception = exception
        self.traceback = traceback
        self.code = code
