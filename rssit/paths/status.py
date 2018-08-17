# -*- coding: utf-8 -*-


import rssit.status
import datetime


def process(server, path, normpath, options):
    server.send_response(200, "OK")
    #server.send_header("Content-Type", "text/
    server.end_headers()

    out = "Now: %s\n\n\nPaths:\n\n" % datetime.datetime.time(datetime.datetime.now())

    for item in rssit.status.processing:
        out += "%s - %s\n" % (item["path"], datetime.datetime.time(item["date"]))

    out += "\n\nURLs:\n\n"

    for item in rssit.status.fetching:
        out += "%s - %s\n" % (item["url"], datetime.datetime.time(item["date"]))

    out += "\n\nAPI calls:\n\n"

    for item in rssit.status.apis:
        out += "%s:%s - %s\n" % (item["item"]["apidef"]["name"], item["item"]["endpoint"], datetime.datetime.time(item["date"]))

    out += "\n\nProcesses:\n\n"

    for item in rssit.status.processes:
        out += "%s - %s\n" % (item["item"], datetime.datetime.time(item["date"]))

    server.wfile.write(bytes(
        out
    , "UTF-8"))


infos = [{
    "path": "status",
    "process": process
}]
