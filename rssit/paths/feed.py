# -*- coding: utf-8 -*-


import rssit.generator
import rssit.serializer
import rssit.formats
import re
import io
import traceback


def process(server, path, normpath, options):
    splitted = normpath.split("/")

    if len(splitted) < 2 or splitted[1] == "":
        server.send_response(301, "Moved")
        server.send_header("Location", "/")
        server.end_headers()
        return

    newpath = re.sub("^" + splitted[0] + "/", "", normpath)

    config = rssit.generator.get_config(newpath)
    config.update(options)
    config["fullpath"] = path
    result = rssit.generator.process(server, config, newpath)

    if not result:
        server.send_response(500, "ISE: Feed")
        server.end_headers()

        server.wfile.write(bytes("An unknown error occurred while trying to generate feed", "UTF-8"))
        return

    if result is True:
        return

    server.send_response(200, "OK")

    result_format = result[0]
    if not result_format in rssit.formats.formats:
        # print error?
        return

    server.send_header("Content-type", rssit.formats.formats[result_format]["content-type"])
    server.end_headers()

    str_result = result[1]

    if type(str_result) not in [str, bytes]:
        str_result = rssit.serializer.process(config, str_result, result_format).encode('utf-8')
        #str_result = ujson.dumps(str_result).encode('utf-8')

    server.wfile.write(str_result)

    import gc
    gc.collect()


infos = [{
    "path": "f",
    "process": process
}]
