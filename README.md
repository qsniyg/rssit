# RSSit
RSS/Atom feed generator for various (mainly social media) websites, including Twitter and Instagram.

## Supported websites

As of the time of writing:

 * Facebook
 * Flickr
 * Instagram (images, videos, albums, stories, livestreams/replays, messages, news)
 * Livedoor
 * Naver blogs (posts, search)
 * Various news websites (posts, search, but it's a mess at the moment)
 * Reddit (messages only)
 * Soundcloud
 * Tistory (posts, search, categories, tags)
 * Tumblr
 * Twitter
 * Vine (deprecated due to vine's closure)
 * Weibo
 * XE (search only)

This list may change. Check https://github.com/qsniyg/rssit/tree/master/rssit/generators to see the full list.

## Requirements

RSSit requires Python 3, and various packages outlined in requirements.txt.
You can install them automatically via:

`$ pip install -r requirements.txt`

## Installation

None required.

## Usage

`$ python rssit.py`

By default, it will serve at `http://localhost:8123/`.

Access it via your web browser, and submit the URL you wish to generate a feed for.
If it's supported, it will return a link to the feed.

You can also run rssit as a command-line application by submitting a URL path directly (without the leading http://...):

`$ python rssit.py '/f/twitter/u/Support'`

## Configuration

### Intro

Configuration is primarily done at `~/.config/rssit/config.ini`. Here is a sample configuration:

    [core]
    hostname = localhost
    port = 8123

    [default]
    output = rss

You can also add specific configurations for any generator and feed.

    [twitter]
    output = atom

    [twitter/u/Support]
    title = Support from Twitter
    description = Twitter's Support User

Since configuration is applied from parent folders to children,
with the configuration above, http://localhost:8123/f/twitter/u/Support will result in this configuration:

    title = Support from Twitter
    description = Twitter's Support User
    output = atom

Configuration is lazily applied, so the following entry is perfectly acceptable,
and would modify the previous URL's configuration accordingly:

    [twitter/u]
    output = rss

If you only wish to modify the configuration per-request, you can do so via standard GET request parameters:

    http://localhost:8123/f/twitter/u/Support?title=Support&output=atom

You can also modify the configuration on the command-line:

`$ python rssit.py '/f/twitter/u/Support' output=rss "title=Support from Twitter"`

### Hooks

Other applications can be hooked to run at any stage of the feed generation process.
One such application is [download.py](https://github.com/qsniyg/dlscripts/blob/master/download.py),
which uses data from the "social" output format to download media.

To use download.py, clone the [dlscripts repo](https://github.com/qsniyg/dlscripts/) somewhere,
and add the following to your configuration:

    social_hooks = python path/to/download.py

RSSit will then send the data to the program's stdin.

To disable hooks entirely (useful for one-off usages):

    nohooks = true

### Common options

While each generator can have their own options, these options will modify most generators' behaviour

 * `output` - Output format. Possible options:
   * `social` - Simple format used to describe most social media-like posts (represented in JSON)
   * `feed` - General format used to describe a feed (every generator must generate to this directly
        or to a format such as social that supports generating to this)
   * `rss` - RSS
   * `atom` - Atom
 * `count` - Minimum amount of entries to return. Currently not all generators support this. Possible values:
   * `-1` - All entries (can be very slow)
   * `0` - No entries
   * `1` - Minimum possible number of entries (fastest)
   * `n` - Minimum of `n` entries
 * `brackets` - Adds the generator's name in brackets to the title of the feed, e.g. '[Twitter] TwitterDev'
 * `title` - Title of the feed
 * `description` - Description of the feed
 * `timeout` - Timeout for downloads submitted by the generator
 * `proxy` - Proxy for downloads
 * `httpheaders_[...]` - Sets an HTTP header for downloads, for example `httpheaders_Cookie = ...`
     (useful for at least Instagram and Weibo)

### Core options

Options that affect the core engine for RSSit

 * `hostname` - Network hostname. This is used for self-referencing URLs within RSSit
 * `port` - Port to run RSSit
