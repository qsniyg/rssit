# -*- coding: utf-8 -*-

import re

def process(server, path, normpath, options):
    server.send_response(200, "OK")
    server.send_header("Content-type", "text/html")
    server.end_headers()

    url = path[len("/player/"):]

    type_ = ""
    if re.search(r"\.m3u8[^/]*$", url):
        type_ = "type='application/x-mpegURL'"

    server.wfile.write(bytes(
        "<html>"
        "  <head>"
        "    <title>rssit player</title>"
        "    <link href='https://vjs.zencdn.net/7.0.3/video-js.css' rel='stylesheet'>"
        "    <script src='https://vjs.zencdn.net/7.0.3/video.js'></script>"
        "    <script src='https://unpkg.com/videojs-contrib-hls/dist/videojs-contrib-hls.js'></script>"
        "    <style>"
        "      body {margin:0;background:black;width:100%%;height:100%%;text-align:center}"
        "      .video-js {height:100%%;width:100%%}"
        "    </style>"
        "  </head>"
        "  <body>"
        "    <video class='video-js vjs-default-skin' preload='auto' data-setup='{}' controls>"
        "      <source src='%s' %s>"
        "    </video>"
        "  </body>"
        "</html>" % (
            url,
            type_
        ), "UTF-8"))


infos = [{
    "path": "player",
    "process": process
}]
