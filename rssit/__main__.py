# -*- coding: utf-8 -*-


import rssit.config
import rssit.http


appname = "rssit"


def main():
    config = rssit.config.get(appname)
    rssit.http.serve(int(config["core"]["port"]), config)
