# -*- coding: utf-8; python-indent-offset: 4 -*-


import rssit.generator
import rssit.generators.all
import rssit.serializer
import rssit.formats
import re
import traceback


stylestr = """<style>
      table {
        border: 1px solid black;
        border-collapse: collapse;
        padding: 0;
        margin: 0;
      }
      td, th {
        border: 1px solid black;
        padding: .5em;
      }
      hr { padding: 0; margin: 0; }
    </style>
"""


def init():
    for generator_name in rssit.generators.all.generator_dict:
        generator = rssit.generators.all.generator_dict[generator_name]
        if "init" in generator:
            generator["init"](rssit.generator.get_config(generator_name))


def unload():
    for generator_name in rssit.generators.all.generator_dict:
        generator = rssit.generators.all.generator_dict[generator_name]
        if "unload" in generator:
            generator["unload"](rssit.generator.get_config(generator_name))


def update():
    #unload()
    #init()
    pass


def process(server, path, normpath, options):
    splitted = normpath.split("/")

    if len(splitted) < 2 or splitted[1] == "":
        server.send_response(200, "OK")
        server.end_headers()

        genstr = ""
        for generator_name in rssit.generators.all.generator_dict:
            generator = rssit.generators.all.generator_dict[generator_name]
            genstr += "<tr><td><a href='/f/%s'>/f/%s</a></td><td>%s</td></tr>\n" % (generator_name, generator_name, generator["display_name"])

        respstr = """
<html>
  <head>
    <title>RSSit - Feeds</title>
    %s
  </head>
  <body>
    <h1 style='text-align:center'>Feeds</h1>
    <br /><br />
    <center><table>%s</table></center>
  </body>
</html>
""" % (
    stylestr,
    genstr
)

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

        introstr = ""
        if "intro" in generator and generator["intro"]:
            introstr = "<br /><center><p>%s</p></center>" % rssit.util.htmlify(generator["intro"])

        endstr = ""
        if "endpoints" in generator and generator["endpoints"]:
            for endpoint_name in generator["endpoints"]:
                endpoint = generator["endpoints"][endpoint_name]
                if "internal" in endpoint and endpoint["internal"]:
                    continue
                endstr += "<tr><td>/%s</td><td>%s</td></tr>\n" % (endpoint_name, endpoint["name"])
        else:
            endstr = "(n/a)"

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
    %s
  <head>
  <body>
    <h1 style='text-align:center'>%s</h1>
    %s
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
    stylestr,
    generator["display_name"],
    introstr,
    endstr,
    optionstr
)
        server.wfile.write(bytes(respstr, "UTF-8"))
        return

    try:
        result = rssit.generator.process(server, config, newpath)
    except Exception as e:
        raise rssit.util.HTTPErrorException(e, traceback.format_exc(), config.get("http_error", 500))

    if not result:
        errorcode = 500
        if "http_error" in config and config["http_error"] != 200:
            errorcode = config["http_error"]

        server.send_response(errorcode, "ISE: Feed")
        server.end_headers()

        server.wfile.write(bytes("An unknown error occurred while trying to generate feed", "UTF-8"))
        return

    if result is True:
        return

    server.send_response(200, "OK")

    result_format = result[0]
    if result_format not in rssit.formats.formats:
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
    "init": init,
    "process": process
}]
