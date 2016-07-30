#!/usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(SCRIPT_DIR))

from rssit import __main__

if __name__ == "__main__":
    __main__.main()
