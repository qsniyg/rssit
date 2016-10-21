# -*- coding: utf-8 -*-


import feedgen.feed


def process_base(result, config):
    fg = feedgen.feed.FeedGenerator()

    fg.title(result["title"])

    if "description" in result:
        fg.description(result["description"])
    else:
        fg.description(result["title"])

    if "id" in result:
        fg.id(result["id"])
    elif "url" in result:
        fg.id(result["url"])

    fg.link(href=result["url"], rel="alternate")


    for entry in result["entries"]:
        fe = fg.add_entry()

        fe.link(href=entry["url"], rel="alternate")

        if "id" in entry:
            fe.id(entry["id"])
        else:
            fe.id(entry["url"])

        fe.title(entry["title"])

        if "description" in entry:
            fe.description(entry["description"])
        else:
            fe.description(entry["title"])

        fe.author(name=entry["author"])
        fe.published(entry["date"])

        if "updated_date" in entry:
            fe.updated(entry["updated_date"])
        else:
            fe.updated(entry["created_at"])

        fe.content(entry["content"], type="html")

    return fg


def process_rss(result, config):
    return process_base(result, config).rss_str(encoding="ascii")


def process_atom(result, config):
    return process_base(result, config).atom_str(encoding="ascii")


infos = [
    {
        "input": "feed",
        "output": "rss",
        "process": process_rss
    },
    {
        "input": "feed",
        "output": "atom",
        "process": process_atom
    }
]
