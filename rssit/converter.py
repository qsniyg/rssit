# -*- coding: utf-8 -*-


import rssit.converters.all
import rssit.serializer
import rssit.status
import rssit.config
import rssit.globals
import os.path
import copy
import pprint
import threading
import subprocess
import re


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
        if key == input:
            continue
        path = get_path(key, output)

        if path is not None:
            current_path = make_list(cd[input][key])
            current_path.extend(path)

            cd[input][output] = current_path
            return current_path

    return None


class runthread(threading.Thread):
    def __init__(self, p, data, cmd):
        threading.Thread.__init__(self)
        self.p = p
        self.data = data
        self.cmd = cmd

    def run(self):
        status_obj = rssit.status.add_process(self.cmd)
        self.p.communicate(input=self.data)
        self.p.wait()
        rssit.status.remove_process(status_obj)
        #print("Done")
        self.data = None


def parse_wblist(contents):
    lines = contents.split("\n")
    basedict = {}
    for line in lines:
        line = line.strip()

        if len(line) == 0 or line[0] == "#":
            continue

        current = basedict
        for i in range(len(line)):
            if line[i] not in current:
                current[line[i]] = {}
            current = current[line[i]]
        current[" "] = True

    return basedict


def read_wblist(filename):
    if filename in rssit.globals.wblist_cache:
        return rssit.globals.wblist_cache[filename]

    load_paths = rssit.config.get_config_paths(rssit.globals.appname, filename)
    for path in load_paths:
        if os.path.exists(path):
            with open(path, 'r') as wbfile:
                contents = wbfile.read()
                #rssit.globals.wblist_cache[path] = contents
                rssit.globals.wblist_cache[path] = parse_wblist(contents)
                return rssit.globals.wblist_cache[path]
    return None


def in_wblist_old(wblist, value):
    contents = read_wblist(wblist)
    if type(contents) is not str:
        return False

    lines = contents.split("\n")
    for line in lines:
        if type(value) == list:
            if line in value:
                return True
        elif type(value) == str and line == value:
            return True
    return False


def in_wblist(wblist, value):
    parsed = read_wblist(wblist)
    if type(parsed) is not dict:
        return False

    current = parsed
    for i in range(len(value)):
        if value[i] not in current:
            return False
        current = current[value[i]]

    return " " in current


def runhooks(config, data, format):
    if "nohooks" in config and config["nohooks"] is True:
        return

    hookslist = []

    for key in config:
        if re.match("^" + format + "_hooks[0-9]*$", key):
            hookslist.append((key, config[key]))
    #hooksname = format + "_hooks"

    #if hooksname not in config:
    #    return
    if len(hookslist) == 0:
        return

    #hookslist = config[hooksname].split(";")
    hooksdata = []

    if format == "social":
        newdata = rssit.util.simple_copy(data)
        newdata["entries"] = []

        # TODO: optimize, this is horribly inefficient
        for key, hook in hookslist:
            currentdata = rssit.util.simple_copy(newdata)

            for entry in data["entries"]:
                can_add = True
                has_whitelist = False

                for ckey in config:
                    if (not ckey.startswith(key)) or ckey == key:
                        continue

                    sckey = ckey[len(key):]
                    whitelist = False
                    if sckey.startswith(".whitelist."):
                        whitelist = True

                        if can_add and not has_whitelist:
                            can_add = False
                            has_whitelist = True
                    elif not sckey.startswith(".blacklist."):
                        continue

                    # len("whitelist") == len("blacklist")
                    sckey = sckey[len(".whitelist."):]

                    if sckey not in entry:
                        continue

                    valin = in_wblist(config[ckey], entry[sckey])

                    if valin:
                        if whitelist:
                            can_add = True
                        else:
                            can_add = False
                            break

                if can_add:
                    currentdata["entries"].append(entry)
            if len(currentdata["entries"]) == 0:
                hooksdata.append(None)
            else:
                processed = str(rssit.serializer.process(config, currentdata, format))
                if type(processed) != str:
                    hooksdata.append(None)
                else:
                    hooksdata.append(processed)
    else:
        processed = str(rssit.serializer.process(config, data, format))
        if type(processed) != str:
            return

        for key, hook in hookslist:
            hooksdata.append(processed)

    i = 0
    for key, hook in hookslist:
        if hooksdata[i] is None:
            continue

        p = subprocess.Popen(hook, stdin=subprocess.PIPE,
                             stdout=None, stderr=None, close_fds=True,
                             shell=True)
        rt = runthread(p, bytes(hooksdata[i], "utf-8"), hook)
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
