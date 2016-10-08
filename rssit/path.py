# -*- coding: utf-8 -*-


import importlib
import os.path
import re
import rssit.paths.all
import rssit.config
import traceback
import urllib.parse


def questionmark(path):
    if "?" not in path:
        return (path, {})

    firstidx = path.index("?")
    kvs = path[firstidx:]
    idx = 0

    options = {}

    while idx < len(kvs):
        kvs = kvs[idx + 1:]

        if "&" in kvs:
            idx = kvs.index("&")
        else:
            idx = len(kvs)

        kv = kvs[:idx]

        if not "=" in kv:
            continue

        eq = kv.index("=")

        key = kv[:eq]
        value = rssit.config.parse_value_simple(urllib.parse.unquote(kv[eq + 1:]))

        options[key] = value

    return (path[:firstidx], options)


def process(server, path):
    normpath = re.sub("^/*", "", os.path.normpath(path))
    newpath, options = questionmark(normpath)
    path_name = newpath.split("/")[0].lower()

    path_list = rssit.paths.all.paths_dict

    if not path_name in path_list:
        path_name = "404"

    try:
        output = path_list[path_name]["process"](server, path, newpath, options)
        return output
    except Exception as err:
        server.send_response(500, "Internal Server Error")
        server.end_headers()

        server.wfile.write(bytes(traceback.format_exc(), "UTF-8"))
