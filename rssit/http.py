# -*- coding: utf-8 -*-


import http.server
import socketserver
import rssit.path


try:
    port
except NameError:
    port = 0


def do_GET_real(self):
    self.protocol_version = "HTTP/1.1"

    rssit.path.process(self, self.path)


class handler(http.server.SimpleHTTPRequestHandler):
    allow_reuse_address = True

    def server_bind(self):
        self.socket.setsockopt(self.socket.SOL_SOCKET,
                               self.socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(self.socket.SOL_SOCKET,
                               self.socket.SO_REUSEPORT, 1)
        self.socket.bind(self.server_address)

    def do_GET(self):
        self.protocol_version = "HTTP/1.1"

        rssit.path.process(self, self.path)
        #do_GET_real(self)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def serve(wanted_port):
    global port

    port = wanted_port

    while True:
        try:
            print("Trying port %i" % port)
            #socketserver.TCPServer(('', port), handler).serve_forever()
            socketserver.TCPServer.allow_reuse_address = True
            ThreadedTCPServer(('', port), handler).serve_forever()
        except OSError as exc:
            if exc.errno != 98:
                raise

            port += 1
        else:
            break
