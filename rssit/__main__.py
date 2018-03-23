# -*- coding: utf-8 -*-


import rssit.config
import rssit.http
import sys
import rssit.generator
import rssit.globals
import rssit.update
import rssit.args
import rssit.cli
import rssit.paths.all
import gc
import lxml.etree
import signal


config_model = {
    "core": {
        "name": "Core",
        "description": "Options affecting the core application",

        "options": {
            "hostname": {
                "name": "Hostname",
                "value": "localhost",
                "description": "Network hostname"
            },

            "port": {
                "name": "Port",
                "value": 8123,
                "description": "Port number"
            }
        }
    },

    "default": {
        "name": "Default",
        "description": "Default options",

        "options": {
            "output": {
                "name": "Output format",
                "value": "rss",
                "description": "Output format for feeds"
            },

            "timeout": {
                "name": "Download timeout",
                "value": 40,
                "description": "Timeout for downloads (in seconds)"
            },

            "count": {
                "name": "Count",
                "value": 1,
                "description": "Minimum amount of items to return (1 for default, 0 for none, -1 for all)"
            },

            "brackets": {
                "name": "Use brackets",
                "value": False,
                "description": "Add brackets to show generator name, e.g. '[Twitter] TwitterDev'"
            },

            "title": {
                "name": "Title",
                "value": "",
                "description": "Custom title (leave blank for default)"
            },

            "description": {
                "name": "Description",
                "value": "",
                "description": "Custom description (leave blank for default)"
            },

            "picture_tag": {
                "name": "Use <picture>",
                "value": True,
                "description": "Use the <picture> tag when converting from social to feed"
            }
        }
    }
}


def signal_handler(signal, frame):
    print("Killing")
    rssit.update.kill()


def update():
    rssit.globals.config["model"] = config_model
    rssit.globals.config["model"].update(rssit.generator.get_model())


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    gc.enable()
    #gc.set_debug(gc.DEBUG_LEAK)

    lxml.etree.set_default_parser(lxml.etree.XMLParser(dtd_validation=False, collect_ids=False))

    rssit.update.update()

    rssit.config.load()

    url = rssit.args.parse_args(sys.argv)
    if url:
        return rssit.cli.serve(url)

    for path_name in rssit.paths.all.paths_dict:
        path = rssit.paths.all.paths_dict[path_name]
        if "init" in path:
            path["init"]()

    core = rssit.config.get_section("core")
    rssit.http.serve(core["port"])

    return 0
