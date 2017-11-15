# -*- coding: utf-8 -*-


import rssit.util


def htmlify(text):
    return rssit.util.link_urls(text).replace("\n", "<br />\n")


def process(result, config):
    feed = {}

    for key in result.keys():
        if key != "entries":
            feed[key] = rssit.util.simple_copy(result[key])

    feed["entries"] = []

    for entry in result["entries"]:
        caption = entry["caption"]

        if not caption:
            caption = "(n/a)"

        if "description" in entry and entry["description"] is not None:
            basecontent = htmlify(entry["description"])
        else:
            basecontent = htmlify(caption)

        if "extratext" in entry and entry["extratext"]:
            basecontent += "\n<hr />\n"
            basecontent += htmlify(entry["extratext"])

        basetitle = caption.replace("\n", " ")

        if entry["author"] != result["author"]:
            content = "<p><em>%s</em></p><p>%s</p>" % (
                entry["author"],
                basecontent
            )

            title = "%s: %s" % (
                entry["author"],
                basetitle
            )
        else:
            content = "<p>%s</p>" % basecontent
            title = basetitle

        if entry["videos"]:
            for video in entry["videos"]:
                if "image" in video and video["image"]:
                    content += "<p><em>Click to watch video</em></p>"

                    content += "<a href='%s'><img src='%s' alt='(thumbnail)'/></a>" % (
                        rssit.util.get_local_url("/player/" + video["video"], norm=False),
                        video["image"]
                    )
                else:
                    content += "<p><em><a href='%s'>Video</a></em></p>" % video["video"]

        if entry["images"]:
            for image in entry["images"]:
                if type(image) not in [list, tuple]:
                    image = [image]

                for theimage in image:
                    content += "<p><img src='%s' alt='(image)'/></p>" % theimage

        thisentry = {
            "url": entry["url"],
            "title": title,
            "author": entry["author"],
            "date": entry["date"],
            "content": content
        }

        if "updated_date" in entry:
            thisentry["updated_date"] = entry["updated_date"]

        feed["entries"].append(thisentry)

    return feed


infos = [{
    "input": "social",
    "output": "feed",
    "process": process
}]
