# -*- coding: utf-8 -*-


import rssit.converters.all
import rssit.serializer
import copy
import threading
import subprocess


def make_list(x):
    if type(x) != list:
        return [x]
    else:
        return x


def get_path(input, output):
    cd = rssit.converters.all.converters_dict

    if input not in cd:
        return None

    if output in cd[input]:
        return make_list(cd[input][output])

    for key in cd[input].keys():
        path = get_path(key, output)

        if path is not None:
            current_path = make_list(cd[input][key])
            current_path.extend(path)

            cd[input][output] = current_path
            return current_path

    return None


class runthread(threading.Thread):
    def __init__(self, p, data):
        threading.Thread.__init__(self)
        self.p = p
        self.data = data

    def run(self):
        self.p.communicate(input=self.data)
        self.p.wait()


def runhooks(config, data, format):
    if "nohooks" in config and config["nohooks"] is True:
        return

    hooksname = format + "_hooks"

    if hooksname not in config:
        return

    hookslist = config[hooksname].split(";")

    processed = str(rssit.serializer.process(config, data, format))

    if type(processed) != str:
        return

    for hook in hookslist:
        p = subprocess.Popen(hook, stdin=subprocess.PIPE,
                             stdout=None, stderr=None, close_fds=True,
                             shell=True)
        rt = runthread(p, bytes(processed, "utf-8"))
        rt.start()


def process(config, data, input, output):
    path = get_path(input, output)

    if not path and input == output:
        runhooks(config, data, input)
        return data

    if not path:
        return False

    for i in path:
        runhooks(config, data, i["input"])

        data = i["process"](data, config)

    runhooks(config, data, output)

    return data
