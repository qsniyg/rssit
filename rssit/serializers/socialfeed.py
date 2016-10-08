# -*- coding: utf-8 -*-


import rssit.util
import ujson


def process(data):
    newdata = rssit.util.simplecopy(data)
    newdata["config"] = rssit.util.simplecopy(data["config"])

    for entry in newdata["entries"]:
        entry["date"] = int(entry["date"].timestamp())

        if "updated_date" in entry:
            entry["updated_date"] = int(entry["updated_date"].timestamp())

    return ujson.dumps(newresult)


infos = [
    {
        "name": "social",
        "process": process
    },

    {
        "name": "feed",
        "process": process
    }
]
