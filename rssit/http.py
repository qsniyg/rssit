# -*- coding: utf-8 -*-


import http.server
import socketserver
import re
import rssit.generate


config = {}


class handler(http.server.SimpleHTTPRequestHandler):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def do_GET(self):
        self.protocol_version = "HTTP/1.1"

        path = re.sub('^/*', '', self.path)

        if path == "core" or not path in config:
            self.send_response(404, "Not found")
            self.end_headers()

            self.wfile.write(bytes("404", "UTF-8"))
            return

        text = rssit.generate.process(config[path])
        if text == None:
            self.send_response(500, "URL error")
            self.end_headers()

            print("URL %s not supported" % config[path]["url"])

            return

        if config[path]["type"] == "rss":
            self.send_response(200, "OK")
            self.send_header("Content-type", "application/rss+xml")
        elif config[path]["type"] == "atom":
            self.send_response(200, "OK")
            self.send_header("Content-type", "application/atom+xml")
        else:
            self.send_response(500, "Type error")
            print("Invalid type for %s, need 'rss' or 'atom', but got '%s'" %
                  (path, config[path]["type"]))

        self.end_headers()

        self.wfile.write(text)


def serve(port, app_config):
    global config
    config = app_config

    while True:
        try:
            print("Trying port %i" % port)
            socketserver.TCPServer(('', port), handler).serve_forever()
        except OSError as exc:
            if exc.errno != 98:
                raise

            port += 1
        else:
            break
