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
import rssit.status
import urllib.parse
import sys
import pprint
import http.cookiejar
import http.cookies
if True:
    import json
else:
    try:
        import rapidjson as json
    except ImportError:
        import json
import random
import sortedcontainers
import collections
import gzip

import io
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


def get_httpheader(config, header):
    goodkey = "httpheader_" + header.lower()
    for key in config:
        if key.lower() == goodkey:
            return config[key]
    return None


def get_random_user_agent(config=None):
    if config is not None:
        useragent = get_httpheader(config, "user-agent")
        if useragent:
            return useragent
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

    status_obj = rssit.status.add_url(url)

    config["http_error"] = 500

    if "head" in kwargs and kwargs["head"]:
        request = urllib.request.Request(url, method="HEAD")
    elif "post" in kwargs and kwargs["post"]:
        request = urllib.request.Request(url, data=kwargs["post"], method="POST")
    elif "method" in kwargs and kwargs["method"]:
        request = urllib.request.Request(url, method=kwargs["method"])
    else:
        request = urllib.request.Request(url)

    httpheaders = {}
    if "http_noextra" not in kwargs:
        httpheaders['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36'
        httpheaders['Pragma'] = 'no-cache'
        httpheaders['Cache-Control'] = 'max-age=0'
        httpheaders['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        #request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36')
        #request.add_header('Pragma', 'no-cache')
        #request.add_header('Cache-Control', 'max-age=0')
        #request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')

        #request.add_header('Accept-Encoding', 'gzip, deflate')
        #request.add_header('Accept-Language', 'ko,en;q=0.9,en-US;q=0.8')

    for key in config:
        if key.startswith("httpheader_"):
            httpheaders[key] = config[key]

    for key in kwargs:
        if key.startswith("httpheader_"):
            httpheaders[key] = kwargs[key]

    headers = {}

    #pprint.pprint(httpheaders)
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

            headers[headername] = httpheaders[key]

    use_cookiejar = False
    cookieprefix = None
    if "http_cookiejar" in kwargs and kwargs["http_cookiejar"] and rinstance:
        use_cookiejar = True
        cookieprefix = "RSSIT:HTTP_COOKIES:" + kwargs["http_cookiejar"] + ":"
        newcookies = {}
        for key in rinstance.scan_iter(match=cookieprefix + "*"):
            cookie = key.replace(cookieprefix, "")
            newcookies[cookie] = rinstance.get(key)
        if len(newcookies) > 0:
            cookies = {}
            if "Cookie" in headers:
                C = http.cookies.SimpleCookie()
                C.load(headers["Cookie"])
                for cookie in C:
                    cookies[cookie] = C[cookie].value
            for cookie in newcookies:
                cookies[cookie] = newcookies[cookie]
            C = http.cookies.SimpleCookie()
            cookiestring = []
            for cookie in cookies:
                C[cookie] = cookies[cookie]
            for cookie in C:
                cookiestring.append(re.sub(r"^ *Cookie: *", "", C[cookie].output(header='Cookie: ')))
            headers["Cookie"] = "; ".join(cookiestring)

    for header in headers:
        request.add_header(header, headers[header])

    if "proxy" in config and config["proxy"]:
        proxy_support = urllib.request.ProxyHandler({"http": config["proxy"]})
        opener = urllib.request.build_opener(proxy_support)
        openf = opener.open
    elif "http_urllib_debug" in config and config["http_urllib_debug"]:
        opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1),
                                             urllib.request.HTTPSHandler(debuglevel=1))
        openf = opener.open
    else:
        openf = urllib.request.urlopen

    finished = False
    times = 0
    ourresponse = b''
    content_length = -1
    content_encoding = None
    while not finished:
        times = times + 1
        if times > 3:
            finished = True

        if content_length > 0:
            request.add_header('Range', 'bytes=%i-%i' % (len(ourresponse), content_length))

        try:
            with openf(request, timeout=int(config["timeout"])) as response:
                for header in response.headers._headers:
                    if header[0].lower() == "content-length":
                        content_length = int(header[1])
                    elif header[0].lower() == "content-encoding":
                        content_encoding = header[1]
                    elif header[0].lower() == "set-cookie" and use_cookiejar:
                        C = http.cookies.SimpleCookie()
                        C.load(header[1])
                        for cookie in C:
                            if "value" not in C[cookie]:
                                continue
                            if rinstance:
                                if "max-age" in C[cookie] and C[cookie]["max-age"] != '' and C[cookie]["max-age"] != '0':
                                    rinstance.setex(cookieprefix + cookie, int(C[cookie]["max-age"]), C[cookie].value)
                                else:
                                    rinstance.setex(cookieprefix + cookie, C[cookie].value)

                charset = response.headers.get_content_charset()

                try:
                    ourresponse += response.read()
                    finished = True
                except http.client.IncompleteRead as e:
                    ourresponse += e.partial

                config["http_error"] = 200

                if content_encoding == "gzip":
                    buf = io.BytesIO(ourresponse)
                    f = gzip.GzipFile(fileobj=buf)
                    ourresponse = f.read()

                rssit.status.remove_url(status_obj)

                if charset and False:
                    try:
                        return ourresponse.decode(charset)
                    except Exception as e:
                        sys.stderr.write("Error decoding charset " + charset + ": " + str(e) + "\n")
                        return ourresponse

                return ourresponse
        except urllib.error.HTTPError as e:
            #pprint.pprint(e.read())
            if e.code == 302:
                # infinite loop
                config["http_error"] = 500
            else:
                config["http_error"] = e.code

            config["http_resp"] = ourresponse

            if e.code == 404 or e.code == 403 or e.code == 410:  # 410: instagram
                rssit.status.remove_url(status_obj)
                raise e
        except Exception as e:
            sys.stderr.write("Other exception while downloading: " + str(e) + "\n")
            rssit.status.remove_url(status_obj)
            raise e

    rssit.status.remove_url(status_obj)


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

        while (total is None or len(nodes) < total) and (has_next_page is not False):
            output = f(maxid)
            if not output or not output[0] or len(output[0]) == 0:
                break

            nodes.extend(output[0])
            if total is None or len(nodes) < total:
                if total is not None:
                    totalnum = str(total)
                else:
                    totalnum = "???"

                sys.stderr.write("\rLoading media (%i/%s)... " % (len(nodes), totalnum))
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

def replace_timezone(dt, target_tz):
    if not need_timezone(dt):
        return dt
    return pytz.timezone(target_tz).localize(dt)

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


def requote_uri(uri):
    parsed = urllib.parse.urlparse(uri)
    newpath = urllib.parse.quote(urllib.parse.unquote(parsed.path))
    return urllib.parse.urlunparse((parsed[0], parsed[1], newpath, parsed[3], parsed[4], parsed[5]))


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
        self.base_redis_key = "RSSIT:" + str(self.name) + ":"

    def now(self):
        return int(datetime.datetime.now().timestamp())

    def get_redis_key(self, key):
        if not self.name:
            return None

        return self.base_redis_key + str(key)

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

        redis_key = self.get_redis_key(key)
        if rinstance and redis_key:
            if self.timeout != 0:
                rinstance.setex(redis_key, self.timeout, json_dumps(value))
            else:
                rinstance.set(redis_key, json_dumps(value))

    def get(self, key):
        self.collect()

        if self.rand > 0 and random.randint(0, self.rand) == 0:
            return None

        redis_key = self.get_redis_key(key)
        if rinstance and redis_key:
            val = rinstance.get(redis_key)
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

    def scan(self, pattern):
        if rinstance:
            for i in rinstance.scan_iter(match=self.get_redis_key(pattern)):
                yield i[len(self.base_redis_key):]
        else:
            for key in self.db:
                if findmatch(pattern, key):
                    yield key

    def collect(self):
        if self.timeout == 0:
            return

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

def findmatch(matchstr, text):
    ti = 0
    mi = 0
    for _i in range(1000):
        if mi >= len(matchstr):
            if ti >= len(text):
                return True
            else:
                return False
        if ti >= len(text):
            if matchstr[mi:] == "*":
                return True
            return False

        if matchstr[mi] != '*':
            if matchstr[mi] != text[ti]:
                return False
            mi += 1
            ti += 1
        else:
            if mi + 1 >= len(matchstr):
                return True

            if findmatch(matchstr[mi+1:], text[ti:]):
                mi += 1
            else:
                ti += 1
    return False

def addhttp(url):
    if not re.search("^[^/]+://", url):
        return "http://" + url
    return url


class HTTPErrorException(BaseException):
    def __init__(self, exception, traceback, code):
        self.exception = exception
        self.traceback = traceback
        self.code = code
