# -*- coding: utf-8 -*-


import copy
import configparser
import xdg.BaseDirectory
import os


default_config = {
    "core": {
        "port": 8080
    },

    "default": {
        "type": "rss",
        "count": 10
    }
}


def parse_file(path):
    config = configparser.ConfigParser()
    config.read(path + "/config")
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


def postprocess(config):
    new_config = {}

    for url in config:
        if url == "default":
            continue

        if url == "core":
            new_config["core"] = config["core"]

        new_config[url] = copy.deepcopy(config["default"])
        new_config[url].update(config[url])

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
