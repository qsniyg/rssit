# -*- coding: utf-8 -*-


import importlib
import rssit.update


def process(server, path, normpath, options):
    importlib.reload(rssit.update)
    rssit.update.update()

    server.send_response(200, "OK")
    server.end_headers()

    server.wfile.write(bytes("Updated code", "UTF-8"))


infos = [{
    "path": "update",
    "process": process
}]
