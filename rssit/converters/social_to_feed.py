# -*- coding: utf-8 -*-


import rssit.util
import sys
import html


def htmlify(text):
    return rssit.util.link_urls(html.escape(text)).replace("\n", "<br />\n")


def do_image(config, image, link=None, alt_img="image"):
    if type(image) not in [list, tuple]:
        image = [image]

    if len(image) == 0:
        sys.stderr.write("0 images\n")
        return None

    content = "<p>"

    linkstart = ""
    linkend = ""
    if link is not None:
        linkstart = "<a href='%s'>" % link
        linkend = "</a>"

    if config["picture_tag"] and False:
        content += linkstart
        content += "<picture>"
        for theimage in image:
            content += "<source srcset='%s' />" % theimage
        content += "<img src='%s' alt='(%s)' />" % (image[0], alt_img)
        content += "</picture>"
        content += linkend
    else:
        alt = ""
        for theimage in image:
            content += "<p>%s<img src='%s' alt='(%s%s)'/>%s</p>" % (
                linkstart,
                theimage, alt_img, alt,
                linkend
            )
            alt = ", alt"

    content += "</p>"
    return content


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

        ft = ""
        if "coauthors" in entry and type(entry["coauthors"]) is list:
            if len(entry["coauthors"]) > 0:
                ft = " ft. " + ", ".join(entry["coauthors"])

        if entry["author"] != result["author"]:
            content = "<p><em>%s%s</em></p><p>%s</p>" % (
                entry["author"],
                ft,
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
                videourls = video["video"]
                if type(videourls) not in [tuple, list]:
                    videourls = [videourls]
                alt = ""
                for videourl in videourls:
                    if "image" in video and video["image"]:
                        content += "<p><em>Click to watch video%s</em></p>" % alt

                        content += do_image(config, video["image"], rssit.util.get_local_url("/player/" + videourl, norm=False), "thumbnail")
                    else:
                        content += "<p><em><a href='%s'>Video%s</a></em></p>" % (videourl, alt)
                    alt = " (alt)"

        if entry["images"]:
            for image in entry["images"]:
                image_content = do_image(config, image)
                if image_content is not None:
                    content += image_content
                """if type(image) not in [list, tuple]:
                    image = [image]

                if len(image) == 0:
                    sys.stderr.write("0 images\n")
                    continue

                if config["picture_tag"]:
                    content += "<p><picture>"
                    for theimage in image:
                        content += "<source srcset='%s' />" % theimage
                    content += "<img src='%s' alt='(image)' />" % image[0]
                    content += "</picture></p>"
                else:
                    content += "<p>"
                    for theimage in image:
                        content += "<p><img src='%s' alt='(image)'/></p>" % theimage
                    content += "</p>"
                """

        thisentry = {
            "url": entry["url"],
            "title": title,
            "author": entry["author"],
            "date": entry["date"],
            "content": content
        }

        if "guid" in entry:
            thisentry["id"] = entry["guid"]

        if "updated_date" in entry:
            thisentry["updated_date"] = entry["updated_date"]

        feed["entries"].append(thisentry)

    return feed


infos = [{
    "input": "social",
    "output": "feed",
    "process": process
}]
