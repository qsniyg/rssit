# -*- coding: utf-8 -*-


import importlib
import os.path
import re
import rssit.paths.all
import traceback


def process(server, path):
    normpath = re.sub("^/*", "", os.path.normpath(path))
    path_name = normpath.split("/")[0].lower()

    path_list = rssit.paths.all.paths_dict

    if not path_name in path_list:
        path_name = "404"

    try:
        output = path_list[path_name]["process"](server, path, normpath)
    except Exception as err:
        server.send_response(500, "Internal Server Error")
        server.end_headers()

        server.wfile.write(bytes(traceback.format_exc(), "UTF-8"))
    return output
