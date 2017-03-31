# -*- coding: utf-8 -*-


def process(result, config):
    result["config"] = config
    return result


infos = [{
    "input": "social",
    "output": "social",
    "process": process
}]
