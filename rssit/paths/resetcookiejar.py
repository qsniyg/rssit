# -*- coding: utf-8 -*-

try:
    import redis
except ImportError:
    redis = None

rinstance = None
try:
    rinstance = redis.StrictRedis(host='localhost', db=1, charset="utf-8", decode_responses=True)
except:
    rinstance = None


def process(server, path, normpath, options):
    if not rinstance:
        server.send_response(500, "No redis")
        server.end_headers()

        server.wfile.write(bytes("No redis", "UTF-8"))
        return

    splitted = normpath.split("/")

    pattern = "RSSIT:HTTP_COOKIES:*"
    if len(splitted) > 1 and splitted[1] != "":
        pattern = "RSSIT:HTTP_COOKIES:" + splitted[1] + ":*"

    server.send_response(200, "OK")
    server.end_headers()

    out = ""
    do_reset = "really_reset" in options and options["really_reset"] == "yes"
    if not do_reset:
        out = "To reset, run this again with ?really_reset=yes\n\n"
    else:
        out = "The keys below were deleted\n\n"

    for key in rinstance.scan_iter(match=pattern):
        if do_reset:
            rinstance.delete(key)
        out += key + "\n"

    server.wfile.write(bytes(out, "UTF-8"))


infos = [{
    "path": "resetcookiejar",
    "process": process
}]
