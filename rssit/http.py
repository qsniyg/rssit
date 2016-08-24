# -*- coding: utf-8 -*-


import http.server
import socketserver
import re
import rssit.generate
import rssit.config
import rssit.update
import importlib
import types


try:
    config
except NameError:
    config = {}
    port = 0


def do_GET_real(self):
    self.protocol_version = "HTTP/1.1"

    path = re.sub('^/*', '', self.path)
    path_base = re.sub(r'(\..*)/.*', r'\1', path)

    if path == "reload":
           global config
           config = rssit.config.get("rssit")
           self.send_response(200, "OK")
           self.end_headers()

           self.wfile.write(bytes("Configuration reloaded", "UTF-8"))
           return

    if path == "update":
           importlib.reload(rssit.update)
           rssit.update.update()

           self.send_response(200, "OK")
           self.end_headers()

           self.wfile.write(bytes("Updated code", "UTF-8"))
           return

    if rssit.config.is_builtin(path) or not path_base in config:
           self.send_response(404, "Not found")
           self.end_headers()

           self.wfile.write(bytes("404", "UTF-8"))
           return

    if path != path_base:
           return rssit.generate.http(config[path_base], path, self)

    text = rssit.generate.process(config[path], "http://localhost:%i/%s" % (port, path))
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


class handler(http.server.SimpleHTTPRequestHandler):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def do_GET(self):
        do_GET_real(self)


def serve(wanted_port, app_config):
    global config, port

    config = app_config
    port = wanted_port

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
