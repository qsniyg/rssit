# -*- coding: utf-8 -*-


def process(server, path, normpath):
    server.send_response(404, "Not found")
    server.end_headers()

    server.wfile.write(bytes("404", "UTF-8"))


infos = [{
    "path": "404",
    "process": process
}]
