# -*- coding: utf-8 -*-


import rssit.config
import rssit.http
import rssit.generate
import ujson
import sys


appname = "rssit"


def main():
    config = rssit.config.get(appname)

    if len(sys.argv) >= 3:
        config_section = {
            "url": sys.argv[2]
        }
        newconfig = rssit.config.postprocess_section(config, config_section)

        result = rssit.generate.direct(newconfig, sys.argv[1])

        print(rssit.generate.get_json(result, newconfig))
        return

    rssit.http.serve(int(config["core"]["port"]), config)
