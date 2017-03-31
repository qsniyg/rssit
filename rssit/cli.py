# -*- coding: utf-8 -*-


import rssit.path
import sys
import io


returncode = 0


class fakeserver():
    def __init__(self):
        self.wfile = io.BytesIO()
        pass

    def send_response(self, code, message=""):
        global returncode
        if code < 200 or code >= 300:
            returncode = code
            sys.stderr.write(str(code) + ": " + message + "\n")
        else:
            returncode = 0

    def send_header(self, key, value=""):
        if returncode != 0:
            sys.stderr.write(key + ": " + str(value) + "\n")

    def end_headers(self):
        pass


def serve(url):
    myserver = fakeserver()
    rssit.path.process(myserver, url)
    if returncode == 0:
        sys.stdout.write(myserver.wfile.getvalue().decode('utf-8'))
    else:
        sys.stderr.write(myserver.wfile.getvalue().decode('utf-8') + "\n")
    return returncode
