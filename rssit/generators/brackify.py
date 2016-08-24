# -*- coding: utf-8 -*-


import re
import rssit.util
import json
import demjson
import datetime
from dateutil.tz import *


info = {
    "name": "Brackify",
    "codename": "brackify",
    "config": {
        "ranks": 4
    }
}


def check(url):
    return re.match(r"^https?://(?:\w+\.)?brackify\.com/bracket/[0-9]*", url) != None


def commame(s):
    return "{:,}".format(int(s))


def gen_matchups(decoded, items):
    out_str = ""
    out_str += "<tr><td><h1 style='text-align:center'>Matchups:</h1></td></tr>"
    out_str += "<tr><td align='center'><div style='margin:auto'>"

    matchups = []

    slots = decoded["bracket"]["slotToRound"]
    slot_keys = list(sorted(slots.keys()))
    actualround = decoded["bracket"]["actualRound"]
    initialitems = decoded["bracket"]["initialItems"]

    top = None
    for slot in slot_keys:
        if slots[slot] != actualround:
            continue

        if not top:
            top = initialitems[slot]
        else:
            matchups.append("%s-%s" % (top, initialitems[slot]))
            top = None

    matchup_keys = list(sorted([int(x.split('-')[0]) for x in matchups]))

    votesid = "votes-" + decoded["bracket"]["currentRound"]
    for matchup_k in matchup_keys:
        for matchup in matchups:
            if matchup.startswith(str(matchup_k)):
                break

        splitted = matchup.split('-')
        item1 = items[splitted[0]]
        item2 = items[splitted[1]]

        if int(item2[votesid]) > int(item1[votesid]):
            item1, item2 = item2, item1

        out_str += """
<div style='display:inline-block;margin:0;padding:0;padding-left:.5em;padding-right:.5em'>
  <div style='display:inline-block'>
    <img src='%s' width='96px' height='96px' alt='%s' title='%s' />
    <br />
    <h3 style='margin:0;padding:0;text-align:center'>%s</h3>
  </div>
  <hr width='32px' />
  <div style='display:inline-block'>
    <img src='%s' width='96px' height='96px' alt='%s' title='%s' />
    <br />
    <h3 style='margin:0;padding:0;text-align:center'>%s</h3>
  </div>
</div>
<br style='display:none'/><br style='display:none' />""" % (
    item1["img150x150"], item1["name"], item1["name"], commame(item1[votesid]),
    item2["img150x150"], item2["name"], item2["name"], commame(item2[votesid])
    )

    out_str += "</div></tr></td>"

    return out_str


def generate(config, webpath):
    match = re.match(r"^https?://(?:\w+\.)?brackify\.com/bracket/[0-9]*", config["url"])

    if match == None:
        return None

    url = config["url"]

    ranks = config["ranks"]

    data = rssit.util.download(url)

    jsondatare = re.search(r"Y\.namespace.*?BRACKIFY.*?CONFIG = (?P<json>.*?});\\n", str(data))
    if jsondatare == None:
        return None

    jsondata = jsondatare.group("json")
    jsondata = rssit.util.fix_surrogates(jsondata.encode('utf-8').decode('unicode-escape'))

    decoded = json.loads(jsondata)

    out_str = ""
    out_str += "<table><tr><td><h1 style='text-align:center'>Rankings:</h1></td></tr>"

    has_champion = "A1" in decoded["bracket"]["initialItems"]

    items = decoded["items"]
    votes = {}
    for item in items:
        votes[int(items[item]["totalVotes"])] = item

    keys = list(votes.keys())
    keys.sort()

    rank = {}
    x = 1
    for i in reversed(keys):
        rank[x] = votes[i]
        x = x + 1

    out_str += "<tr><td align='center'><table style='margin:auto;padding:0'>"
    for i in range(1, ranks+1):
        item = items[rank[i]]
        is_eliminated = item["isEliminated"]

        if has_champion:
            if decoded["bracket"]["initialItems"]["A1"] == rank[i]:
                is_eliminated_str = "- CHAMPION"
            else:
                is_eliminated_str = ""
        else:
            if is_eliminated:
                is_eliminated_str = " - ELIMINATED"
            else:
                is_eliminated_str = ""

        out_str += """
<tr>
  <td style='vertical-align:middle'>
    <h1 style='margin:0;padding:0;padding-left:.3em;padding-right:.3em;'>#%s</h1>
  </td>
  <td>
    <img src='%s' width='96px' height='96px' style='margin:0;padding:0;padding-top:.3em;padding-bottom:.3em'/>
  </td>
  <td>
    <table style='margin:0;padding:0;padding-left:.5em'>
      <tr>
        <td>
          <h2>%s%s</h2>
        </td>
      </tr>
      <tr>
        <td>
          <h3>Votes: %s</h3>
        </td>
      </tr>
    </table>
  </td>
</tr>""" % (
            str(i), item["img150x150"], item["name"], is_eliminated_str, commame(item["totalVotes"])
        )

    out_str += "</table></td></tr>"

    if not has_champion:
        out_str += gen_matchups(decoded, items)

    out_str += "</table>"

    if "debug" in config:
        f = open("/tmp/bracketout.html", "w")
        f.write(out_str)
        f.close()
        return


    feed = {
        "title": decoded["bracket"]["title"],
        "description": decoded["bracket"]["subtitle"],
        "entries": []
    }


    now = rssit.util.localize_datetime(datetime.datetime.now())

    if "new_entry" in config:
        new_entry = True
    else:
        new_entry = False

    if new_entry:
        id = config["url"] + "/" + str(int(now.timestamp()))
        title = "%s - %s (Updated: %s)" % (decoded["bracket"]["title"],
                                           decoded["bracket"]["subtitle"],
                                           str(now))
    else:
        id = config["url"]
        title = "%s - %s" % (decoded["bracket"]["title"],
                             decoded["bracket"]["subtitle"])

    feed["entries"].append({
        "url": config["url"],
        "id": id,
        "title": title,
        "author": "Brackify",
        "date": now,
        "content": out_str
    })


    return feed
