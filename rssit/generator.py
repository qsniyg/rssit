# -*- coding: utf-8 -*-


import rssit.generators.all
import rssit.converter
import rssit.config


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


def get_url(url):
    for i in rssit.generators.all.generator_dict:
        newurl = i["get_url"](url)

        if newurl:
            return newurl


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


    if config["brackets"] and type(result) == dict and "title" in result:
        result["title"] = "[%s] %s" % (generator.info["name"],
                                       result["title"])

    format = config["output"]

    return (format, rssit.converter.process(config, result, result_format, format))
