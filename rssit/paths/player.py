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
    elif re.search(r"\.mpd[^/]*$", url):
        type_ = "type='application/dash+xml'"

    server.wfile.write(bytes(
        "<html>\n"
        "  <head>\n"
        "    <title>rssit player</title>\n"
        "    <link href='https://vjs.zencdn.net/7.0.3/video-js.css' rel='stylesheet'>\n"
        "    <script src='https://vjs.zencdn.net/7.0.3/video.js'></script>\n"
        "    <script src='https://unpkg.com/videojs-contrib-hls/dist/videojs-contrib-hls.js'></script>\n"
        "    <script src='https://cdn.dashjs.org/latest/dash.all.min.js'></script>\n"
        "    <script src='https://unpkg.com/videojs-contrib-dash/dist/videojs-dash.js'></script>\n"
        "    <style>\n"
        "      body {margin:0;background:black;width:100%%;height:100%%;text-align:center}\n"
        "      .video-js {height:100%%;width:100%%}\n"
        "    </style>\n"
        "  </head>\n"
        "  <body>\n"
        "    <video class='video-js vjs-default-skin' preload='auto' data-setup='{}' controls>\n"
        "      <source src='%s' %s>\n"
        "    </video>\n"
        "  </body>\n"
        "</html>\n" % (
            url,
            type_
        ), "UTF-8"))


infos = [{
    "path": "player",
    "process": process
}]
