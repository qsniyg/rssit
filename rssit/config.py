# -*- coding: utf-8 -*-


import copy
import configparser
import xdg.BaseDirectory
import os
import os.path
import rssit.globals
import re


def get_config_paths(appname, filename):
    paths = reversed(list(xdg.BaseDirectory.load_config_paths(appname)))

    config_paths = []

    for path in paths:
        config_paths.append(os.path.join(path, filename))

    return config_paths


def get_load_paths(appname):
    return get_config_paths(appname, "config.ini")


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

    configp = configparser.ConfigParser()
    configp.read_dict(config)

    with open(path, 'w') as configfile:
        configp.write(configfile)


def parse_value_simple(value):
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False

    if re.search(r"[^0-9.-]", value) or len(value) > 10:
        return value

    try:
        ival = int(value)
        if ival < 2**32:
            return ival
        else:
            return value
    except ValueError:
        return value


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


def value_to_str(value):
    if type(value) == bool:
        if value:
            return "true"
        else:
            return "false"
    if value is None:
        return "null"
    return str(value)


def parse_section(section, section_key):
    for key in section:
        section[key] = parse_value_simple(section[key])


def parse_sections(sections):
    for section_key in sections:
        parse_section(sections[section_key], section_key)


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


def get_config_model_obj(options, model, config, config_profile=None):
    options.update(copy.deepcopy(get_model_options(model)))
    options.update(copy.deepcopy(config))
    if config_profile is not None:
        options.update(copy.deepcopy(config_profile))
    options.update(copy.deepcopy(rssit.globals.config["config"].get("args", {})))


def get_config_profile_section(section, profile=None):
    if profile is None:
        return None

    return rssit.globals.config["config"].get(section + "@" + str(profile), {})


def get_config_model(options, section, profile=None):
    config = rssit.globals.config["config"].get(section, {})
    model = rssit.globals.config["model"].get(section, {})

    config_profile = get_config_profile_section(section, profile)

    get_config_model_obj(options, model, config, config_profile)


def get_section(section, profile=None):
    options = {}

    if "/" not in section:
        get_config_model(options, section, profile)
        return options

    get_config_model(options, "default", profile)

    splitted = section.split("/")[:-1]
    for i in range(len(splitted)):
        split = os.path.join(splitted[0], *splitted[1:i+1])
        get_config_model(options, split, profile)

    options.update(copy.deepcopy(rssit.globals.config["config"].get(section, {})))
    config_profile = get_config_profile_section(section, profile)
    if config_profile is not None:
        options.update(copy.deepcopy(config_profile))
    options.update(copy.deepcopy(rssit.globals.config["config"].get("args", {})))

    return options


def load():
    rssit.globals.config["config"] = {}
    rssit.globals.config["wblist_cache"] = {}

    config_paths = get_load_paths(rssit.globals.appname)
    save_path = get_save_path(rssit.globals.appname)

    if len(config_paths) > 0:
        rssit.globals.config["config"] = parse_files(config_paths)
