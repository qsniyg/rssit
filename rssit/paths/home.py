# -*- coding: utf-8 -*-


import rssit.generator


def process(server, path, normpath, options):
    server.send_response(200, "OK")
    server.send_header("Content-type", "text/html")
    server.end_headers()

    if "url" in options and len(options["url"]) > 0:
        displayurl = options["url"]

        urls = rssit.generator.get_urls(displayurl)

        if len(urls) > 0:
            urltext = "<strong>Feed URL(s):</strong><br /><br />"

            for i in urls:
                urltext += i + "<br />"
        else:
            urltext = "<strong>URL not supported</strong>"
    else:
        displayurl = ""
        urltext = ""

    server.wfile.write(bytes(
        "<html>"
        "  <head>"
        "    <title>rssit</title>"
        "  </head>"
        "  <body>"
        "    <h1 style='text-align:center'>rssit</h1>"
        "    <br /><br />"
        "    <center><form action=/ method=get>"
        "      <strong>External URL:</strong><br /><br />"
        "      <input name=url type=text value='%s' autofocus style='width:500px' />"
        "      <input type=submit />"
        "      <br /><em><small>(e.g. https://twitter.com/Support)</small></em>"
        "    </form></center>"
        "    <br /><br />"
        "    <center>%s</center>"
        "  </body>"
        "</html>" % (
            displayurl, urltext
        ), "UTF-8"))


infos = [{
    "path": "",
    "process": process
}]
