# -*- coding: utf-8 -*-


import rssit.generators.all
import rssit.converter
import rssit.config
import rssit.util


def get_model():
    model = {}
    gd = rssit.generators.all.generator_dict

    for generator_key in gd:
        generator = gd[generator_key]

        model[generator["name"]] = {
            "name": generator["display_name"],
            "description": "Default options for " + generator["display_name"],

            "options": generator["config"]
        }

    return model


def get_config(path):
    return rssit.config.get_section(path)


def get_urls(url):
    urls = []
    gd = rssit.generators.all.generator_dict

    for i in gd:
        newurl = gd[i]["get_url"](url)

        if newurl:
            fullpath = "/f/" + gd[i]["name"] + "/" + newurl
            urls.append(rssit.util.get_local_url(fullpath))

    return urls


def process(server, config, path):
    splitted = path.split("/")

    generator_name = splitted[0]
    gd = rssit.generators.all.generator_dict

    if not generator_name in gd:
        return

    generator = gd[generator_name]

    if path.startswith("/"):
        genpath = path[len(generator_name) + 1:]
    else:
        genpath = path[len(generator_name):]

    process_result = generator["process"](server, config, genpath)

    if process_result == None:
        return

    if type(process_result) == tuple:
        result_format = process_result[0]
        result = process_result[1]
    elif process_result == True:
        return True


    if len(config["title"]) > 0:
        result["title"] = config["title"]

    if len(config["description"]) > 0:
        result["description"] = config["description"]

    if config["brackets"] and type(result) == dict and "title" in result:
        result["title"] = "[%s] %s" % (generator["display_name"],
                                       result["title"])

    config["generator"] = generator["name"]

    format = config["output"]

    return (format, rssit.converter.process(config, result, result_format, format))
