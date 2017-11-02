# -*- coding: utf-8 -*-


def process(server, path, normpath, options):
    server.send_response(200, "OK")
    server.send_header("Content-type", "text/html")
    server.end_headers()

    url = path[len("/player/"):]

    server.wfile.write(bytes(
        "<html>"
        "  <head>"
        "    <title>rssit player</title>"
        "    <script src='https://cdn.dashjs.org/latest/dash.all.min.js'></script>"
        "    <style>"
        "      body {margin:0;background:black;text-align:center}"
        "      video {height:100%%;}"
        "    </style>"
        "  </head>"
        "  <body>"
        "    <video data-dashjs-player autoplay src='%s' controls></video>"
        "  </body>"
        "</html>" % (
            url
        ), "UTF-8"))


infos = [{
    "path": "player",
    "process": process
}]
