# rssit
RSS/Atom feed generator for various websites, including Twitter and Instagram.

## Supported websites

As of the time of writing:

 * Flickr
 * Instagram
 * Twitter
 * Vine
 
This list may change. Check https://github.com/qsniyg/rssit/tree/master/rssit/generators to see the full list.

## Requirements

 * python3
 * python-beautifulsoup4
 * python-feedgen (https://pypi.python.org/pypi/feedgen/)
 * python-xdg
 * python-ujson (https://pypi.python.org/pypi/ujson)
 
## Installation

None required.

## Usage

`$ python rssit.py`

By default, it will serve at `http://localhost:8123/`

Access it via your web browser, and submit the URL you wish to generate a feed for.
If it's supported, it will return a link to the feed.

## Configuration

Configuration is done at `~/.config/rssit/config.ini`. Here is a sample configuration:

    [core]
    hostname = localhost
    port = 8123
    
    [default]
    output = rss
    
You can also add specific configurations for any generator and feed:

    [twitter]
    output = atom
    
    [twitter/u/Support]
    title = Support from Twitter
    description = Twitter's Support User

If you only want to change the configuration per-request, you can do so by using standard GET request parameters:

    http://localhost:8123/f/twitter/u/Support?title=Support&output=atom
