import bs4
import ujson
import demjson
import sys
import urllib.request
import urllib.parse
from dateutil.parser import parse
import re
import html
import pprint
import rssit.util
import datetime


# for news1: http://news1.kr/search_front/search.php?query=[...]&collection=front_photo&startCount=[0,20,40,...]
# for starnews: http://star.mt.co.kr/search/index.html?kwd=[...]&category=PHOTO
# for articleList-based: http://stardailynews.co.kr/news/articleList.html?page=1&sc_area=A&sc_word=[...]&view_type=sm
# for tvdaily: http://tvdaily.asiae.co.kr/searchs.php?section=17&searchword=[...]&s_category=2


# http://stackoverflow.com/a/18359215
def get_encoding(soup):
    encod = soup.find("meta", charset=True)
    if encod:
        return encod["charset"]

    encod = soup.find("meta", attrs={'http-equiv': "Content-Type"})
    if not encod:
        encod = soup.find("meta", attrs={"Content-Type": True})

    if encod:
        content = encod["content"]
        match = re.search('charset *= *(.*)', content, re.IGNORECASE)
        if match:
            return match.group(1)

    raise ValueError('unable to find encoding')


def get_url(url):
    base = "/url/"
    if url.startswith("quick:"):
        base = "/qurl/"
        url = url[len("quick:"):]

    if url.startswith("//"):
        url = url[len("//"):]

    url = re.sub(r"^[^/]*://", "", url)

    regexes = [
        "entertain\.naver\.com/",
        "find\.joins\.com/",
        "isplus\.joins\.com/",
        "news1.kr/search_front/",
        "topstarnews.net/search.php",
        "star\.mt\.co\.kr/search",
        "osen\.mt\.co\.kr/search",
        "stardailynews\.co\.kr/news/articleList",
        "liveen.co.kr/news/articleList",
        "tvdaily\.asiae\.co\.kr/searchs",
        "chicnews\.mk\.co\.kr/searchs",
        "search\.hankyung\.com",
        "search\.chosun\.com",
        "mydaily.co.kr/.*/search",
        "search.mbn.co.kr",
        "newsen\.com",
        "xportsnews\.com"
    ]

    found = False
    for regex in regexes:
        match = re.search(regex, url)
        if match:
            found = True

    if not found:
        return None

    return base + url


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
            break
        else:
            tag = None

    if data:
        return (tag, data)

    return tag


def get_title(myjson, soup):
    if myjson["author"] == "topstarnews":
        og_title = soup.find("meta", attrs={"itemprop": "name"})
        if og_title:
            return html.unescape(og_title["content"])

    if ((myjson["author"] in [
            "ettoday",
            "koreastardaily",
            "chosun"
    ]) or (
        "sbscnbc.sbs.co.kr" in myjson["url"]
    )):
        title = get_selector(soup, [
            ".block_title",  # ettoday
            "#content-title > h1",  # koreastardaily
            ".title_author_2011 #title_text",  # chosun
            ".atend_top .atend_title"  # sbscnbc
        ])
        if title and len(title) > 0:
            return title[0].text

    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title:
        return html.unescape(og_title["content"])
    elif "search" in myjson["url"]:
        return "(search)"


def get_author(url):
    if "naver." in url:
        return "naver"
    if ".joins.com" in url:
        return "joins"
    if "news1.kr/" in url:
        return "news1"
    if "topstarnews.net" in url:
        return "topstarnews"
    if "star.mt.co.kr" in url:
        return "starnews"
    if "osen.mt.co.kr" in url:
        return "osen"
    if "stardailynews.co.kr" in url:
        return "stardailynews"
    if "tvdaily.asiae.co.kr" in url:
        return "tvdaily"
    if "hankyung.com" in url:
        return "hankyung"
    if "liveen.co.kr" in url:
        return "liveen"
    if ".chosun.com" in url:
        return "chosun"
    if "mydaily.co.kr" in url:
        return "mydaily"
    if "mbn.co.kr" in url:
        return "mbn"
    if "chicnews.mk.co.kr" in url:
        return "chicnews"
    if "newsen.com" in url:
        return "newsen"
    if "hankooki.com" in url:
        return "hankooki"
    if "ettoday.net" in url:
        return "ettoday"
    if "koreastardaily.com" in url:
        return "koreastardaily"
    if "segye.com" in url:
        return "segye"
    if "xportsnews.com" in url:
        return "xportsnews"
    if "sbs.co.kr" in url:
        return "sbs"
    return None


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
    #print(parse(date))
    if not date:
        return None
    return rssit.util.localize_datetime(parse(date))


def get_date(myjson, soup):
    if myjson["author"] in [
            "ettoday"
            ]:
        return parse_date(-1)

    if "sbs.co.kr" in myjson["url"]:
        datetag = soup.select(".date > meta[itemprop='datePublished']")
        if datetag:
            return parse_date(datetag[0]["content"])

    datetag = get_selector(soup, [
        ".article_info .author em",
        ".article_tit .write_info .write",
        "#article_body_content .title .info",  # news1
        "font.read_time",  # chicnews
        ".gisacopyright",
        "#content-title > h2",  # koreastardaily
        ".read_view_wrap .read_view_date",  # mydaily
        ".date_ctrl_2011 #date_text",  # chosun
        "#_article font.read_time",  # tvdaily
        ".article_head > .clearfx > .data",  # segye
        "#articleSubecjt .newsInfo",  # xportsnews
        "em.sedafs_date",  # sbs program
        "#content > .wrap_tit > p.date",  # sbsfune
        ".atend_top .atend_reporter"  # sbs cnbc
    ])

    if not datetag:
        sys.stderr.write("no recognizable date\n")
        return

    date = None
    for date_tag in datetag:
        if myjson["author"] == "koreastardaily":
            date = parse_date(date_tag.contents[0])
        else:
            date = parse_date(date_tag.text)
        ##if myjson["author"] == "naver":
        ##    if not "오후" in date_tag.text:
        ##        continue
        ##    date = parse(date_tag.text.replace("오후", ""))
        ##else:
        ##    date = parse_date(date_tag.text)

    return date


def is_album(myjson, soup):
    return (
        (myjson["author"] == "hankooki" and "mm_view.php" in myjson["url"]) or
        (myjson["author"] == "sbs" and "program.sbs.co.kr" in myjson["url"])
    )


def end_getimages(myjson, soup, oldimages):
    images = []
    for imagesrc in oldimages:
        image_full_url = urllib.parse.urljoin(myjson["url"], imagesrc)
        images.append(get_max_quality(image_full_url))

    return images


def get_images(myjson, soup):
    if myjson["author"] == "hankooki" and "mm_view.php" in myjson["url"]:
        jsondatare = re.search(r"var *arrView *= *(?P<json>.*?) *;\n", str(soup))
        if not jsondatare:
            sys.stderr.write("No json data!\n")
            return None
        jsondata = str(jsondatare.group("json"))
        decoded = demjson.decode(jsondata)
        images = []
        for img in decoded:
            images.append(get_max_quality(img["photo"]))
        return images

    if myjson["author"] == "chosun" and "html_dir" in myjson["url"]:
        jsondatare = re.findall(r"_photoTable._photoIdx[+][+]. *= *new *Array *[(]\"([^\"]*)\"", str(soup))
        if jsondatare:
            return end_getimages(myjson, soup, jsondatare)

    imagestag = get_selector(soup, [
        "#adiContents img",
        "#article_body_content div[itemprop='articleBody'] td > img",  # news1
        ".article .img_pop_div > img", # chosun
        "#content .news_article #viewFrm .news_photo center > img", # segye
        ".article img",
        "#article img",
        ".articletext img",
        "#_article table[align='center'] img",
        "#_article img.view_photo",
        "#_article .article_photo img",
        "#articleBody img",
        "#articleBody .iframe_img img:nth-of-type(2)",
        "#newsContent .iframe_img img:nth-of-type(2)",
        "#articeBody .img_frame img",
        "#textBody img",
        "#news_contents img",
        "#arl_view_content img",
        ".articleImg img",
        "#newsViewArea img",
        "#articleContent img",
        "#articleContent #img img",
        "#newsContent img.article-photo-mtn",
        "#article_content img",
        "div[itemprop='articleBody'] img",
        "div[itemprop='articleBody'] img.news1_photo",
        "div[itemprop='articleBody'] div[rel='prettyPhoto'] img",
        "div[itemprop='articleBody'] .centerimg img",
        "div[itemprop='articleBody'] .center_image img",
        ".center_image > img",
        ".article_view img",
        "img#newsimg",
        ".article_photo img",
        ".articlePhoto img",
        "#__newsBody__ .he22 td > img",
        ".article_image > img",
        "#CmAdContent img",
        ".article_outer .main_image p > img, .article_outer .post_body p img",
        ".article-img img",
        ".portlet .thumbnail img",
        "#news_textArea img",
        ".news_imgbox img",
        ".view_txt img",
        "#IDContents img",
        "#view_con img",
        "#newsEndContents img",
        ".articleBox img",
        ".rns_text img",
        "#article_txt img",
        "#ndArtBody .imgframe img",
        ".view_box center img",
        ".newsbm_img_wrap > img",
        ".article .detail img",
        "#articeBody img",
        "center table td a > img",  # topstarnews search
        ".gisaimg > ul > li > img",  # hankooki
        ".part_thumb_2 .box_0 .pic img",  # star.ettoday.net
        "#content-body p > img",  # koreastardaily
        "#adnmore_inImage div[align='center'] > table > tr > td > a > img",  # topstarnews article
        ".sprg_main_w #post_cont_wrap p > img",  # sbs program
        "#content > #etv_news_content img[alt='이미지']",  # sbsfune
        "#content .atend_center img[alt='이미지']",  # sbscnbc
    ])

    if not imagestag:
        return

    images = []
    for image in imagestag:
        imagesrc = image["src"]
        if image.has_attr("data-src"):
            imagesrc = image["data-src"]
        image_full_url = urllib.parse.urljoin(myjson["url"], imagesrc)
        images.append(get_max_quality(image_full_url))

    return images


def get_description(myjson, soup):
    desc_tag = get_selector(soup, [
        "#article_content #adiContents",
        "#article_body_content .detail",
        "#CmAdContent",  # chicnews
        "#GS_Content",  # hankooki
        "#wrap #read_left #article",  # mydaily
        ".photo_art_box",  # chosun
        "#article_2011",  # chosun
        "#_article .read",  # tvdaily
        "#viewFrm #article_txt",  # segye
        "#CmAdContent .newsView div[itemprop='articleBody']",  # xportsnews
        ".sprg_main_w #post_cont_wrap",  # sbs
        "#content > #etv_news_content",  # sbsfune
        ".w_article_left > .article_cont_area",  # sbs news
        "#content .atend_center"  # sbs cnbc
    ])

    if not desc_tag:
        return

    #return "\n".join(list(desc_tag[0].strings))
    return str(desc_tag[0])


def clean_url(url):
    return url.replace("\n", "").replace("\r", "").replace("\t", "")


def get_article_url(url):
    return url


def get_segye_photos(myjson, soup):
    strsoup = str(soup)
    match = re.search(r"var *photoData *= *eval *\( *' *(\[.*?\]) *' *\) *;", strsoup)
    if not match or not match.group(1):
        return

    jsondatastr = match.group(1)
    jsondata = demjson.decode(jsondatastr)
    print(jsondata)


def do_api(config, path):
    author = re.sub(r".*?/api/([^/]*).*", "\\1", path)

    if re.match(r".*?/api/[^/]*/([^/?]+)", path):
        query = re.sub(r".*?/api/[^/]*/([^/?]+)", "\\1", path)
    else:
        query = None

    myjson = {
        "title": author,
        "author": author,
        "url": None,
        "config": {
            "generator": "news"
        },
        "entries": []
    }

    articles = []
    if author == "joins":
        url = 'http://searchapi.joins.com/search_jsonp.jsp?query=' + query
        if "collection" in config and config["collection"]:
            url += "&collection=" + config["collection"]
        url += "&sfield=ART_TITLE"
        if "startCount" in config and config["startCount"]:
            url += "&startCount=" + str(config["startCount"])
        url += "&callback=?"
        url = rssit.util.quote_url1(url)
        myjson["url"] = url
        data = rssit.util.download(url)
        data = re.sub(r"^[?][(](.*)[)];$", "\\1", data)
        jsondata = demjson.decode(data)
        collections = jsondata["SearchQueryResult"]["Collection"]

        def remove_tags(text):
            return text.replace("<!HS>", "").replace("<!HE>", "")

        for collection in collections:
            documentset = collection["DocumentSet"]
            if documentset["Count"] == 0:
                continue

            documents = documentset["Document"]
            for document in documents:
                field = document["Field"]
                thumb_url = urllib.parse.urljoin("http://pds.joins.com/", field["ART_THUMB"])
                thumb_url = get_max_quality(thumb_url)
                fday = field['SERVICE_DAY']
                syear = int(fday[0:4])
                smonth = int(fday[4:6])
                sday = int(fday[6:8])
                date = datetime.datetime(year=syear, month=smonth, day=sday).timestamp()
                date += int(field['SERVICE_TIME'])
                date = parse_date(date)
                eurl = "http://isplus.live.joins.com/news/article/article.asp?total_id="
                eurl += field["DOCID"]
                articles.append({
                    "url": eurl,
                    "caption": remove_tags(field["ART_TITLE"]),
                    "aid": field["DOCID"],
                    "date": date,
                    "description": remove_tags(field["ART_CONTENT"]),
                    "images": [thumb_url],
                    "videos": []
                })

    if not myjson["url"] or len(articles) == 0:
        return

    for entry_i in range(len(articles)):
        articles[entry_i] = fix_entry(articles[entry_i])
        articles[entry_i]["author"] = author

    return do_article_list(config, articles, myjson)


def fix_entry(entry):
    realcaption = None
    caption = None
    aid = ""
    if "aid" in entry and entry["aid"]:
        aid = entry["aid"] + " "
    if "caption" in entry and entry["caption"]:
        realcaption = entry["caption"].strip()
        caption = aid + realcaption
    entry["media_caption"] = caption
    entry["caption"] = realcaption
    entry["similarcaption"] = realcaption
    return entry


def get_articles(myjson, soup):
    if myjson["author"] == "joins":
        if "isplusSearch" not in myjson["url"]:
            return
    elif myjson["author"] == "news1" or myjson["author"] == "topstarnews" or myjson["author"] == "hankooki":
        if "search.php" not in myjson["url"]:
            return
    elif myjson["author"] in ["starnews", "osen", "mydaily", "mbn"]:
        if "search" not in myjson["url"]:
            return
    elif myjson["author"] == "sbs":
        if "/search/" not in myjson["url"]:
            return
    elif myjson["author"] == "tvdaily" or myjson["author"] == "chicnews":
        if "searchs.php" not in myjson["url"]:
            return
    elif myjson["author"] == "hankyung":
        if "search.hankyung.com" not in myjson["url"]:
            return
    elif myjson["author"] == "chosun":
        if "search.chosun.com" not in myjson["url"]:
            return
    elif myjson["author"] == "newsen":
        if "news_list.php" not in myjson["url"]:
            return
    elif myjson["author"] == "segye":
        if not re.search("search[^./]*\.segye\.com", myjson["url"]):
            if "photoView" in myjson["url"] and False:
                return get_segye_photos(myjson, soup)
            else:
                return
    elif myjson["author"] == "xportsnews":
        if "ac=article_search" not in myjson["url"]:
            return
    else:
        if "news/articleList" not in myjson["url"]:
            return

    articles = []

    parent_selectors = [
        # joins
        {
            "parent": "#news_list .bd ul li dl",
            "link": "dt a",
            "caption": "dt a",
            "date": "dt .date",
            "images": ".photo img",
            "description": "dd.s_read_cr"
        },
        {
            "parent": "#search_contents .bd ul li dl",
            "link": "dt a",
            "caption": "dt a",
            "date": ".date",
            "images": ".photo img"
        },
        # news1 photo
        {
            "parent": ".search_detail .listType3 ul li",
            "link": "a",
            "caption": "a > strong",
            "date": "a .date",
            "images": ".thumb img",
            "aid": lambda soup: re.sub(r".*/\?([0-9]*).*", "\\1", soup.select("a")[0]["href"])
        },
        # news1 list
        {
            "parent": ".search_detail .listType1 ul li",
            "link": "a",
            "caption": ".info a",
            "date": "dd.date",
            "images": ".thumb img",
            "aid": lambda soup: re.sub(r".*/\?([0-9]*).*", "\\1", soup.select("a")[0]["href"])
        },
        # topstarnews
        {
            "parent": "table#search_part_1 > tr > td > table > tr > td",
            "link": "center > table > tr > td > a",
            "caption": "center > table > tr > td > span > a",
            "date": ".street-photo2",
            "images": "center > table > tr > td > a > img",
            "aid": lambda soup: re.sub(r".*[^a-zA-Z0-9_]number=([0-9]*).*", "\\1", soup.select("center > table > tr > td > a")[0]["href"])
        },
        # starnews
        {
            "parent": "#container > #content > .fbox li.bundle",
            "link": ".txt > a",
            "caption": ".txt > a",
            "date": "-1",
            "images": ".thum img",
            "aid": lambda soup: re.sub(r".*[^a-zA-Z0-9_]no=([0-9]*).*", "\\1", soup.select(".txt > a")[0]["href"])
        },
        # osen
        {
            "parent": "#container .searchBox > table tr > td",
            "link": "a",
            "caption": "p.photoView",
            "date": "-1",
            "images": "a > img",
            "aid": lambda soup: re.sub(r".*/([0-9A-Za-z]*)", "\\1", soup.select("a")[0]["href"])
        },
        # liveen
        {
            "parent": "table#article-list > tr > td > table > tr > td > table",
            "link": "td.list-titles a",
            "caption": "td.list-titles a",
            "description": "td.list-summary a",
            "date": "td.list-times",
            "images": ".list-photos img",
            "html": True,
            "aid": lambda soup: re.sub(r".*idxno=([0-9]*).*", "\\1", soup.select("td.list-titles a")[0]["href"])
        },
        # stardailynews
        {
            "parent": "#ND_Warp table tr > td table tr > td table tr > td table",
            "link": "tr > td > span > a",
            "caption": "tr > td > span > a",
            "description": "tr > td > p",
            "date": "-1",
            "images": "tr > td img",
            "html": True,
            "aid": lambda soup: re.sub(r".*idxno=([0-9]*).*", "\\1", soup.select("tr > td > span > a")[0]["href"])
        },
        # newsen
        {
            "parent": "table[align='left'] > tr > td[align='left'] > table[align='center'] > tr[bgcolor]",
            "link": "a.line",
            "caption": "a > b",
            "description": "td[colspan='2'] > a",
            "date": "td[nowrap]",
            "images": "a > img",
            "aid": lambda soup: re.sub(r".*uid=([^&]*).*", "\\1", soup.select("td > a")[0]["href"]),
            "html": True
        },
        # tvdaily
        {
            "parent": "body > table tr > td > table tr > td > table tr > td > table tr > td",
            "link": "a.sublist",
            "date": "span.date",
            "caption": "a.sublist",
            "description": "p",
            "images": "a > img",
            "imagedata": lambda entry, soup: {
                "date": re.sub(r"[^0-9]*", "", soup.select("span.date")[0].text),
                "aid": re.sub(r".*aid=([^&]*).*", "\\1", soup.select("a.sublist")[0]["href"])
            },
            "aid": lambda soup: re.sub(r".*aid=([^&]*).*", "\\1", soup.select("a.sublist")[0]["href"]),
            "html": True
        },
        # hankyung
        {
            "parent": ".hk_news .section_cont > ul.article > li",
            "link": ".txt_wrap > a",
            "caption": ".txt_wrap .tit",
            "description": ".txt_wrap > p.txt",
            "date": ".info span.date_time",
            "images": ".thumbnail img",
            "html": True
        },
        # old chosun
        {
            "parent": ".result_box > section.result > dl",
            "link": "dt > a",
            "caption": "dt > a",
            "description": "dd > a",
            "date": "dt > em",
            "images": ".thumb img",
            "aid": lambda soup: re.sub(r".*/([^/.?&]*).html$", "\\1", soup.select("dt > a")[0]["href"]),
            "html": True
        },
        # new chosun
        {
            "parent": ".schCont_in .search_news_box .search_news",
            "link": "dt > a",
            "caption": "dt > a",
            "description": ".desc",
            "date": ".date",
            "images": ".thumb img",
            "aid": lambda soup: re.sub(r".*/([^/.?&]*).html$", "\\1", soup.select("dt > a")[0]["href"]),
            "html": True
        },
        # mydaily
        {
            "parent": "#wrap > #section_left > .section_list",
            "link": ".section_list_text > dt > a",
            "caption": ".section_list_text > dt > a",
            "description": ".section_list_text > dd",
            "date": ".section_list_text > dd > p",
            "images": ".section_list_img > a > img",
            "aid": lambda soup: re.sub(r".*newsid=([^&]*).*", "\\1", soup.select(".section_list_text > dt > a")[0]["href"]),
            "html": True
        },
        # mbn
        {
            "parent": "#search_result > .collaction_news > ul > li",
            "link": "a",
            "caption": "a > strong",
            "description": "p.desc",
            "date": ".write_time",
            "images": ".thumb img",
            "aid": lambda soup: re.sub(r".*news_seq_no=([^&]*).*", "\\1", soup.select("a")[0]["href"]),
            "html": True
        },
        # chicnews
        {
            "parent": "#container .container_left dl.article",
            "link": ".tit > a",
            "caption": ".tit > a",
            "description": ".subtxt",
            "date": "span.date",
            "images": ".img img",
            "imagedata": lambda entry, soup: {
                "date": re.sub(r"[^0-9]*", "", soup.select("span.date")[0].text),
                "aid": re.sub(r".*aid=([^&]*).*", "\\1", soup.select(".tit > a")[0]["href"])
            },
            "aid": lambda soup: re.sub(r".*aid=([^&]*).*", "\\1", soup.select(".tit > a")[0]["href"]),
            "html": True
        },
        # hankooki
        {
            "parent": "#SectionCenter .news > .pb12",
            "link": "li.title > a",
            "caption": "li.title > a",
            "description": "li.con > a",
            "date": "li.source",
            "images": ".thumb > a > img",
            "aid": lambda soup: re.sub(r".*/[a-zA-Z]*([^/]*)\.htm[^/]*$", "\\1", soup.select("li.title > a")[0]["href"]),
            "html": True,
            "is_valid": lambda soup: soup.select("li.title > a")[0]["href"].strip()
        },
        # hankooki images
        {
            "parent": "#SectionCenter .images > .pr20",
            "link": ".txt > a",
            "caption": ".txt > a",
            "date": "-1",
            "images": ".pic img"
        },
        # segye (doesn't work, needs api call with access token)
        {
            "parent": "#articleArea .area_box",
            "link": ".r_txt .title_cr > a",
            "caption": ".r_txt .title_cr > a",
            "description": ".read_cr > a",
            "date": "span.date",
            "images": ".Pho .photo img",
            "aid": lambda soup: re.sub(r".*/[0-9]*\.htm[^/]*$", "\\1", soup.select(".r_txt .title_cr > a")[0]["href"]),
            "html": True
        },
        # xportsnews
        {
            "parent": "#list_common_wrap > ul.list_news > li",
            "link": "dl.dlist > dt > a",
            "caption": "dl.dlist > dt > a",
            "description": "dl.dlist > dd:nth-of-type(1)",
            "date": "dl.dlist > dd:nth-of-type(2) > span.data",
            "images": ".thumb > a > img",
            "aid": lambda soup: re.sub(r".*entry_id=([0-9]*).*", "\\1", soup.select("dl.dlist > dt > a")[0]["href"]),
            "html": True
        },
        # sbs
        {
            "parent": ".pss_content_w .pssc_inner ul.ps_newslist > li div.psil_inner",
            "link": "a.psil_link",
            "caption": "strong.psil_tit",
            "description": "p.psil_txt",
            "date": "span.psil_info",
            "images": "span.psil_img > img",
            "html": True
        }
    ]

    parenttag = None
    for selector in parent_selectors:
        parenttag = soup.select(selector["parent"])
        if parenttag and len(parenttag) > 0:
            #parenttag = parenttag[0]
            break
        else:
            parenttag = None

    if not parenttag:
        return []

    for a in parenttag:
        if not a.select(selector["link"]):
            # print warning?
            continue

        entry = {}

        link = get_article_url(urllib.parse.urljoin(myjson["url"], clean_url(a.select(selector["link"])[0]["href"])))
        entry["url"] = link

        if not link.strip():
            # empty link
            continue

        date = 0
        if "date" in selector:
            if selector["date"] == "-1":
                date = parse_date(-1)
            else:
                for date_tag in a.select(selector["date"]):
                    try:
                        date = parse_date(date_tag.text)
                        if date:
                            break
                    except Exception as e:
                        pass
        entry["date"] = date

        realcaption = None
        caption = None
        aid = ""
        if "aid" in selector:
            aid = selector["aid"](a) + " "
        if "caption" in selector:
            realcaption = a.select(selector["caption"])[0].text.strip()
            caption = aid + realcaption
        entry["media_caption"] = caption
        entry["caption"] = realcaption
        entry["similarcaption"] = realcaption

        description = None
        if "description" in selector:
            description_tag = a.select(selector["description"])
            description = ""
            for tag in description_tag:
                if len(tag.text)  > len(description):
                    description = tag.text
        else:
            description = realcaption
            if not "html" in selector:
                selector["html"] = True
        entry["description"] = description

        author = get_author(link)
        entry["author"] = author

        imagedata = None
        if "imagedata" in selector:
            imagedata = selector["imagedata"](entry, a)

        images = []
        if "images" in selector:
            image_tags = a.select(selector["images"])
            for image in image_tags:
                image_full_url = urllib.parse.urljoin(myjson["url"], image["src"])
                image_max_url = get_max_quality(image_full_url, imagedata)
                images.append(image_max_url)

        entry["images"] = images
        entry["videos"] = []

        if "is_valid" in selector:
            if not selector["is_valid"](a):
                continue

        #if "html" in selector:
        #    if selector["html"] is True:
        #        selector["html"] = lambda entry: "<p>" + entry["description"] + "</p>" + '\n'.join(["<p><img src='" + x + "' /></p>" for x in entry["images"]])
        #    entry["description"] = selector["html"](entry)

        articles.append(entry)

    return articles


def get_max_quality(url, data=None):
    if "naver." in url:
        url = re.sub("\?.*", "", url)
        #if "imgnews" not in url:
        # do blogfiles

    if ".joins.com" in url:
        url = re.sub("\.tn_.*", "", url)

    if "image.news1.kr" in url:
        url = [re.sub("/[^/.]*\.([^/]*)$", "/original.\\1", url), url]

    if "main.img.topstarnews.net" in url:
        url = url.replace("main.img.topstarnews.net", "uhd.img.topstarnews.net")

    if "uhd.img.topstarnews.net/" in url:
        url = url.replace("/file_attach_thumb/", "/file_attach/")
        url = re.sub(r"_[^/]*[0-9]*x[0-9]*_[^/]*(\.[^/]*)$", "-org\\1", url)

    if "thumb.mtstarnews.com/" in url:
        url = re.sub(r"\.com/[0-9][0-9]/", ".com/06/", url)

    if "stardailynews.co.kr" in url or "liveen.co.kr" in url:
        url = re.sub("/thumbnail/", "/photo/", url)
        url = re.sub(r"_v[0-9]*\.", ".", url)
        baseurl = url

        url = [baseurl, re.sub("\.jpg$", ".gif", baseurl)]

    if "tvdaily.asiae.co.kr" in url or "chicnews.mk.co.kr":
        if data:
            url = url.replace("/tvdaily.asiae", "/image.tvdaily")
            url = url.replace("/thumb/", "/gisaimg/" + data["date"][:6] + "/")
            url = re.sub(r"/[a-zA-Z]*([^/]*)\.[^/]*$", "/" + data["aid"][:10] + "_\\1.jpg", url)

    if "img.hankyung.com" in url:
        url = re.sub(r"\.[0-9]\.([a-zA-Z0-9]*)$", ".1.\\1", url)

    if "img.tenasia.hankyung.com" in url:
        url = re.sub(r"-[0-9]*x[0-9]*\.jpg$", ".jpg", url)

    if "chosun.com" in url:
        url = url.replace("/thumb_dir/", "/img_dir/").replace("/thumbnail/", "/image/").replace("_thumb.", ".")

    if "file.osen.co.kr" in url:
        url = url.replace("/article_thumb/", "/article/")
        url = re.sub(r"_[0-9]*x[0-9]*\.jpg$", ".jpg", url)

    if "img.mbn.co.kr" in url:
        url = re.sub(r"_[^_/?&]*x[0-9]*\.([^_/?&])", ".\\1", url)
        url = re.sub(r"_s[0-9]*\.([^_/?&])", ".\\1", url)

    if "cdn.newsen.com" in url:
        url = url.replace("_ts.gif", ".jpg")

    if "photo.hankooki.com" in url:
        url = url.replace("/photo/", "/original/").replace("/arch/thumbs/", "/arch/original/")
        url = re.sub(r"/(.*\/)t([0-9]*[^/]*)$/", "\\1\\2", url)

    if ".ettoday.net" in url:
        url = re.sub(r"/[a-z]*([0-9]*\.[^/]*)$", "/\\1", url)

    if "xportsnews.com" in url:
        url = re.sub(r"/thm_([^/]*)", "/\\1", url)

    if "img.sbs.co.kr" in url:
        url = re.sub(r"_[0-9]*(\.[^/]*)$", "\\1", url)

    return url


def do_article_list(config, articles, myjson):
    article_i = 1
    quick = config.get("quick", False)
    for article in articles:
        if article is None:
            sys.stderr.write("error with article\n")
            continue
        if quick:
            if not article["caption"]:
                sys.stderr.write("no caption\n")
                return
            if article["date"] == 0:
                sys.stderr.write("no date\n")
                return
            if not article["caption"] or article["date"] == 0:
                sys.stderr.write("no salvageable information from search\n")
                sys.stderr.write(pprint.pformat(article) + "\n")
                return

            if not article["author"]:
                article["author"] = myjson["author"]
            elif article["author"] != myjson["author"]:
                sys.stderr.write("different authors\n")
                return

            myjson["entries"].append(article)
            continue
        article_url = article["url"]
        basetext = "(%i/%i) " % (article_i, len(articles))
        article_i += 1

        sys.stderr.write(basetext + "Downloading %s... " % article_url)
        sys.stderr.flush()

        newjson = None
        try:
            newjson = do_url(config, article_url, article)
        except Exception as e:
            sys.stderr.write("exception: " + e)
            pass
        if not newjson:
            sys.stderr.write("url: " + article_url + " is invalid\n")
            continue

        if newjson["author"] != myjson["author"]:
            sys.stderr.write("current:\n\n" +
                             pprint.pformat(myjson) +
                             "\n\nnew:\n\n" +
                             pprint.pformat(newjson))
            continue

        sys.stderr.write("done\n")
        sys.stderr.flush()

        myjson["entries"].extend(newjson["entries"])
    return myjson


def do_url(config, url, oldarticle=None):
    quick = False
    if "quick" in config and config["quick"]:
        quick = True

    url = urllib.parse.quote(url, safe="%/:=&?~#+!$,;'@()*[]")

    if "post" in config and config["post"]:
        data = rssit.util.download(url, post=config["post"], config=config)
    else:
        data = rssit.util.download(url, config=config)

    soup = bs4.BeautifulSoup(data, 'lxml')

    encoding = "utf-8"
    try:
        encoding = get_encoding(soup)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        pass
    #data = data.decode("utf-8", "ignore")
    if type(data) != str:
        data = data.decode(encoding, "ignore")
    #data = download("file:///tmp/naver.html")

    soup = bs4.BeautifulSoup(data, 'lxml')

    myjson = {
        "title": None,
        "author": None,
        "url": url,
        "config": {
            "generator": "news"
        },
        "entries": []
    }

    author = get_author(url)

    if not author:
        sys.stderr.write("unknown site\n")
        return

    myjson["author"] = author
    myjson["title"] = author

    articles = get_articles(myjson, soup)
    if articles is not None:
        return do_article_list(config, articles, myjson)

    title = get_title(myjson, soup)

    if not title:
        sys.stderr.write("no title\n")
        return

    date = get_date(myjson, soup)

    if not date:
        if oldarticle and "date" in oldarticle and oldarticle["date"]:
            date = oldarticle["date"]
        else:
            sys.stderr.write("no date\n")
            return

    if "albums" in config and config["albums"] or is_album(myjson, soup):
        album = "[" + str(date.year)[-2:] + str(date.month).zfill(2) + str(date.day).zfill(2) + "] " + title
    else:
        album = None

    images = get_images(myjson, soup)
    if not images:
        sys.stderr.write("no images\n")
        images = []
        #return

    description = get_description(myjson, soup)
    if not description:
        sys.stderr.write("no description\n")

    if oldarticle:
        ourentry = oldarticle
    else:
        ourentry = {}

    ourentry.update({
        "caption": title,
        "description": description,
        "album": album,
        "url": url,
        "date": date,
        "author": author,
        "images": images,
        "videos": [] # for now
    })

    myjson["entries"].append(ourentry)

    return myjson


def generate_url(config, url):
    socialjson = do_url(config, url)
    return generate_base(config, socialjson)

def generate_api(config, url):
    socialjson = do_api(config, url)
    return generate_base(config, socialjson)

def generate_base(config, socialjson):
    retval = {
        "social": socialjson
    }

    basefeedjson = rssit.util.simple_copy(socialjson)
    for entry in basefeedjson["entries"]:
        if "realcaption" in entry:
            entry["caption"] = entry["realcaption"]

    feedjson = rssit.converters.social_to_feed.process(basefeedjson, config)

    return {
        "social": socialjson,
        "feed": feedjson
    }


def process(server, config, path):
    if path.startswith("/post/"):
        if "/endpost/" not in config["fullpath"]:
            sys.stderr.write("no /endpost/\n")
            return None
        config["post"] = re.sub(".*?/post/(.*?)/endpost/.*", "\\1", config["fullpath"]).encode("utf-8")
        newpath = re.sub(".*?/endpost", "", path)
        config["fullpath"] = re.sub(".*?/endpost", "", config["fullpath"])
        return process(server, config, newpath)
    if path.startswith("/url/"):
        url = "http://" + re.sub(".*?/url/", "", config["fullpath"])
        return generate_url(config, url)
    elif path.startswith("/qurl/"):
        url = "http://" + re.sub(".*?/qurl/", "", config["fullpath"])
        config["quick"] = True
        return generate_url(config, url)
    elif path.startswith("/api/"):
        return generate_api(config, path)

infos = [{
    "name": "news",
    "display_name": "News",

    "config": {
        "albums": {
            "name": "Albums",
            "description": "Create albums for articles",
            "value": False
        }
    },

    "get_url": get_url,
    "process": process
}]
