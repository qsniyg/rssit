# -*- coding: utf-8 -*-


import copy
import configparser
import xdg.BaseDirectory
import os
import rssit.generate


default_config = {
    "core": {
        "port": 8080
    },

    "default": {
        "type": "rss",
        "count": 10,
        "brackets": True
    }
}


def is_builtin_copy(key):
    return key == "core"

def is_builtin_skip(key):
    return key == "default" or key.startswith("default/")

def is_builtin(key):
    return is_builtin_copy(key) or is_builtin_skip(key)

def is_url(section_key, section):
    return (not is_builtin(section_key)) and "url" in section


def read_file(path):
    config = configparser.ConfigParser()
    config.read(path + "/config")
    return config


def parse_section(section):
    for key in section:
        if section[key] == "true":
            section[key] = True
        elif section[key] == "false":
            section[key] = False
        elif section[key].isdigit():
            section[key] = int(section[key])


def parse_file(path):
    config = read_file(path)

    for section_key in config._sections:
        parse_section(config._sections[section_key])

    return config._sections


def parse_files(paths):
    config = copy.deepcopy(default_config)

    for path in paths:
        file_config = parse_file(path)

        for key in file_config:
            if key in config:
                config[key].update(file_config[key])
            else:
                config[key] = file_config[key]

    return config


def set_generator(section):
    generator = rssit.generate.find_generator(section["url"])

    if generator:
        section["generator"] = generator
    else:
        section["generator"] = None


def postprocess_section(config, section):
    set_generator(section)

    new_section = copy.deepcopy(config["default"])

    new_section.update(copy.deepcopy(section["generator"].info["config"]))

    codename = section["generator"].info["codename"]
    default_section = "default/" + codename

    if default_section in config:
        new_section.update(copy.deepcopy(config[default_section]))

    new_section.update(section)

    return new_section


def postprocess(config):
    new_config = {}

    for url in config:
        if is_builtin(url):
            new_config[url] = config[url]
            continue

        new_config[url] = postprocess_section(config, config[url])

    return new_config


def get(appname):
    config_paths = list(xdg.BaseDirectory.load_config_paths(appname))

    if len(config_paths) == 0 or not os.path.exists(config_paths[0] + "/config"):
        config_paths = [xdg.BaseDirectory.save_config_path(appname)]

        my_config = configparser.ConfigParser()
        my_config.read_dict(default_config)

        with open(config_paths[0] + "/config", 'w') as configfile:
            my_config.write(configfile)

    config_parsed = parse_files(reversed(config_paths))
    return postprocess(config_parsed)
