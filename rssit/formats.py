# -*- coding: utf-8 -*-


formats = {
    "raw": {
        "name": "Raw data",
        "description": "Raw data, used for API calls",
        "content-type": None
    },

    "social": {
        "name": "Social feed",
        "description": "Simplified feed type for social networking websites",
        "content-type": None
    },

    "feed": {
        "name": "Feed",
        "description": "Generic feed type",
        "content-type": None,
    },

    "rss": {
        "name": "RSS Feed",
        "content-type": "application/rss+xml"
    },

    "atom": {
        "name": "Atom Feed",
        "content-type": "application/atom+xml"
    }
}

formats_order = ["atom", "rss", "feed", "social", "raw"]
