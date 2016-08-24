# -*- coding: utf-8 -*-


import datetime
import re
import rssit.util
import bs4
from feedgen.feed import FeedGenerator


def generate(config, path):
    print("hi")

    match = re.match(r"^https?://(?:\w+\.)?twitter.com/(?P<user>[^/]*)", config["url"])

    if match == None:
        return None

    user = match.group("user")

    data = rssit.util.download(config["url"])

    soup = bs4.BeautifulSoup(data, 'lxml')

    fg = FeedGenerator()
    fg.title("[Twitter] %s" % user)
    fg.description("[Twitter] %s" % user)
    fg.id(config["url"])
    fg.link(href=config["url"], rel="alternate")

    for tweet in soup.find_all(attrs={"data-tweet-id": True}):
        timestamp = int(tweet.find_all(attrs={"data-time": True})[0]["data-time"])
        date = rssit.util.localize_datetime(datetime.datetime.fromtimestamp(timestamp, None))

        username = tweet["data-screen-name"]

        link = tweet["data-permalink-path"]

        title = "@%s: " % username
        tweet_text = "<p><em>@%s</em></p><p>" % username

        for text in tweet.select("p.tweet-text"):
            for i in text.children:
                if type(i) is bs4.element.NavigableString:
                    tweet_text += str(i.string)
                    title += str(i.string)
                else:
                    if i.name == "img":
                        tweet_text += i["alt"]
                        title += i["alt"]
                    elif i.name == "a":
                        if "data-expanded-url" in i.attrs:
                            a_url = i["data-expanded-url"]
                            tweet_text += "<a href='%s'>%s</a>" % (a_url, a_url)
                        elif "twitter-hashtag" in i["class"]:
                            tweet_text += "#" + i.b.string
                            title += "#" + i.b.string

        tweet_text += "</p>"

        image_holder = tweet.find_all(attrs={"data-image-url": True})
        if len(image_holder) > 0:
            image_url = image_holder[0]["data-image-url"]
            tweet_text += "<p><img src='%s' /></p>" % image_url

        is_video_el = tweet.select(".AdaptiveMedia-video")
        if len(is_video_el) > 0:
            tweet_id = tweet["data-tweet-id"]
            video_url = "https://twitter.com/i/videos/%s" % tweet_id
            pmp = tweet.select(".PlayableMedia-player")[0]
            preview_url = re.search(r"background-image: *url.'(?P<url>.*?)'",
                                   pmp["style"]).group("url")

            tweet_text += "<p><em>Click to watch video</em></p>"
            tweet_text += "<a href='%s'><img src='%s'/></a>" % (video_url, preview_url)

        title = title.replace("\n", " ")
        tweet_text = tweet_text.replace("\n", "<br />\n")

        fe = fg.add_entry()
        fe.id(link)
        fe.link(href=link, rel="alternate")
        fe.title(title)
        fe.description(title)
        fe.author(name=username)
        fe.published(date)
        fe.content(tweet_text, type="html")

    return fg
