# -*- coding: utf-8 -*-


import importlib
import os.path
import re
import rssit.paths.all


def process(server, path):
    normpath = re.sub("^/*", "", os.path.normpath(path))
    path_name = normpath.split("/")[0].lower()

    path_list = rssit.paths.all.paths_dict

    if not path_name in path_list:
        path_name = "404"

    return path_list[path_name]["process"](server, path, normpath)
