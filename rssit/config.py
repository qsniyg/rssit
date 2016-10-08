# -*- coding: utf-8 -*-


import copy
import configparser
import xdg.BaseDirectory
import os
import os.path
import rssit.globals


def get_load_paths(appname):
    paths = reversed(list(xdg.BaseDirectory.load_config_paths(appname)))

    config_paths = []

    for path in paths:
        config_paths.append(os.path.join(path, "config.ini"))

    return config_paths


def get_save_path(appname):
    return os.path.join(xdg.BaseDirectory.save_config_path(appname), "config.ini")


def read_file(path):
    config = configparser.ConfigParser()
    config.read(path)
    return config


def write_file(path, config):
    dirname = os.path.dirname(path)

    if not os.path.exists(dirname):
        os.path.makedirs(dirname, exist_ok=True)

    configparser = configparser.ConfigParser()
    configparser.read_dict(config)

    with open(path, 'w') as configfile:
        configpwarser.write(configfile)


def parse_value(value, model_value):
    if type(model_value) == bool:
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        else:
            return None

    if type(model_value) == int:
        try:
            return int(value)
        except ValueError:
            return None

    if type(model_value) == float:
        try:
            return float(value)
        except ValueError:
            return None

    return value


def parse_section(section):
    for key in section:
        section[key] = parse_value(section[key])


def parse_sections(sections):
    for section_key in sections:
        parse_section(sections[section_key])


def parse_file(path):
    config = read_file(path)
    parse_sections(config._sections)
    return config._sections


def parse_files(paths):
    config = {}

    for path in paths:
        file_config = parse_file(path)

        for key in file_config:
            if key in config:
                config[key].update(file_config[key])
            else:
                config[key] = file_config[key]

    return config


def get_model_options(model):
    options = {}

    if not "options" in model:
        return options

    for option in model["options"]:
        options[option] = copy.deepcopy(model["options"][option]["value"])

    return options


def get_models_config(models):
    config = {}

    for model in models:
        config.update(get_model_options(model))

    return config


def get_config_model_obj(options, model, config):
    options.update(copy.deepcopy(get_model_options(model)))
    options.update(copy.deepcopy(config))


def get_config_model(options, section):
    config = rssit.globals.config["config"].get(section, {})
    model = rssit.globals.config["model"].get(section, {})

    get_config_model_obj(options, model, config)


def get_section(section):
    options = {}

    if "/" not in section:
        get_config_model(options, section)
        return options

    get_config_model(options, "default")
    get_config_model(options, section.split("/")[0])

    options.update(copy.deepcopy(rssit.globals.config["config"].get(section, {})))

    return options


def load():
    rssit.globals.config["config"] = {}

    config_paths = get_load_paths(rssit.globals.appname)
    save_path = get_save_path(rssit.globals.appname)

    if len(config_paths) > 0:
        rssit.globals.config["config"] = parse_files(config_paths)
