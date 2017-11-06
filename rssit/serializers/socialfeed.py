# -*- coding: utf-8 -*-


import rssit.util
#import ujson


def process(config, data):
    newdata = rssit.util.simplify_copy(data)
    newdata["config"] = rssit.util.simplify_copy(config)
    return rssit.util.json_dumps(newdata)

    for entry in newdata["entries"]:
        entry["date"] = int(entry["date"].timestamp())

        if "updated_date" in entry:
            entry["updated_date"] = int(entry["updated_date"].timestamp())

    return rssit.util.json_dumps(newdata)


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
