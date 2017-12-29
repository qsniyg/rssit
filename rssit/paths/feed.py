# -*- coding: utf-8 -*-


import rssit.generator
import rssit.generators.all
import rssit.serializer
import rssit.formats
import re
import io
import traceback


def process(server, path, normpath, options):
    splitted = normpath.split("/")

    if len(splitted) < 2 or splitted[1] == "":
        server.send_response(200, "OK")
        server.end_headers()

        genstr = ""
        for generator_name in rssit.generators.all.generator_dict:
            generator = rssit.generators.all.generator_dict[generator_name]
            genstr += "<li><a href='/f/%s'>%s</a></li>\n" % (generator_name, generator["display_name"])

        respstr = """
<html>
  <head>
    <title>RSSit - Feeds</title>
  </head>
  <body>
    <h1 style='text-align:center'>Feeds</h1>
    <br /><br />
    <center><ul style='list-style-type:none;padding:0;margin:0'>%s</ul></center>
  </body>
</html>
""" % genstr

        server.wfile.write(bytes(respstr, "UTF-8"))
        return

        #server.send_response(301, "Moved")
        #server.send_header("Location", "/")
        #server.end_headers()
        #return

    newpath = re.sub("^" + splitted[0] + "/", "", normpath)

    config = rssit.generator.get_config(newpath)
    config.update(options)
    config["fullpath"] = path

    if len(splitted) < 3 or (len(splitted) < 4 and splitted[2] == ""):
        server.send_response(200, "OK")
        server.end_headers()

        generator = rssit.generator.get_generator_for_path(newpath)

        endstr = ""
        for endpoint_name in generator["endpoints"]:
            endpoint = generator["endpoints"][endpoint_name]
            if "internal" in endpoint and endpoint["internal"]:
                continue
            endstr += "<tr><td>/%s</td><td>%s</td></tr>\n" % (endpoint_name, endpoint["name"])

        optionstr = ""
        for option_name in generator["config"]:
            option = generator["config"][option_name]
            """description = ""
            if "description" in option and option["description"]:
                description = "<hr /><p>%s</p>" % option["description"]"""
            name = option["name"]
            if "description" in option and option["description"]:
                name = option["description"]
            optionstr += "<tr><td style='vertical-align:top'>%s</td><td>%s</td><td><p>%s</p></td></tr>\n" % (
                option_name,
                rssit.config.value_to_str(option["value"]),
                name
            )
        respstr = """
<html>
  <head>
    <title>RSSit - %s</title>
    <style>
      table {
        border: 1px solid black;
        border-collapse: collapse;
      }
      td, th {
        border: 1px solid black;
        padding: .5em;
      }
      hr { padding: 0; margin: 0; }
    </style>
  <head>
  <body>
    <h1 style='text-align:center'>%s</h1>
    <br /><h2 style='text-align:center'>Endpoints</h2><br />
    <center><table style='border:1;padding:0;margin:0'>%s</table></center>
    <br /><h2 style='text-align:center'>Configuration</h2><br />
    <center><table style='border:1;padding:0;margin:0;max-width:75%%'>
<tr><th>Option</th><th>Default</th><th>Name</th></tr>
      %s
    </table></center>
  </body>
</html>
""" % (
    generator["display_name"],
    generator["display_name"],
    endstr,
    optionstr
)
        server.wfile.write(bytes(respstr, "UTF-8"))
        return

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
