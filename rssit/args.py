# -*- coding: utf-8 -*-


import rssit.config
import rssit.globals


def parse_args(args):
    url = None

    rssit.globals.config["config"]["args"] = {}

    for arg in args[1:]:
        if len(arg) > 0 and arg[0] == '/':
            url = arg
            continue

        if "=" not in arg:
            # ???
            continue

        eq = arg.index("=")

        key = arg[:eq]
        value = rssit.config.parse_value_simple(arg[eq + 1:])

        rssit.globals.config["config"]["args"][key] = value

    return url
