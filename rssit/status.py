# -*- coding: utf-8 -*-


import datetime


try:
    processing
except NameError:
    processing = []


try:
    fetching
except NameError:
    fetching = []


try:
    apis
except NameError:
    apis = []


try:
    processes
except NameError:
    processes = []


def add_path(path):
    obj = {
        "path": path,
        "date": datetime.datetime.now()
    }

    processing.append(obj)
    return obj


def remove_path(obj):
    processing.remove(obj)


def add_url(url):
    obj = {
        "url": url,
        "date": datetime.datetime.now()
    }

    fetching.append(obj)
    return obj


def remove_url(obj):
    fetching.remove(obj)


def add_api(item):
    obj = {
        "item": item,
        "date": datetime.datetime.now()
    }

    apis.append(obj)
    return obj


def remove_api(obj):
    apis.remove(obj)


def add_process(item):
    obj = {
        "item": item,
        "date": datetime.datetime.now()
    }

    processes.append(obj)
    return obj


def remove_process(obj):
    processes.remove(obj)
