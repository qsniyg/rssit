# -*- coding: utf-8 -*-


import rssit.generators.all


def process(config):
    for generator in rssit.generators.all.all_generators:
        result = generator.generate(config)

        if result == None:
            continue

        if config["type"] == "atom":
            return result.atom_str(encoding="ascii")
        elif config["type"] == "rss":
            return result.rss_str(encoding="ascii")
        else:
            return None
