# -*- coding: utf-8 -*-

import rssit.util
import rssit.rest
import pprint
import os.path
import re
import urllib.parse
import datetime
import sys

api = rssit.rest.API({
    "name": "cameo",
    "type": "json",
    "http_noextra": False,
    "headers": {
    },
    "endpoints": {
        "user": {
            "url": rssit.rest.Format("https://www.bookcameo.com/api/user/show/%s", rssit.rest.Arg("user", 0)),
        },
        "order": {
            "url": rssit.rest.Format("https://www.bookcameo.com/api/order/show/%s", rssit.rest.Arg("order", 0))
        }
    }
})


def get_url(config, url):
    match = re.match(r"^(https?://)?(?:www\.)?cameo\.com/+(?P<user>[a-zA-Z0-9]*)/*$", url)

    if match is None:
        return

    return "/u/" + match.group("user")


user_cache = rssit.util.Cache("cameo:user", 48*60*60, 100)
order_cache = rssit.util.Cache("cameo:order", 48*60*60, 100)


def has_required_keys(obj, keys):
    for key in keys:
        if key not in obj:
            return False
    return True


def cache_user(user):
    if not has_required_keys(user, "_id", "id", "username", "role"):
        sys.stderr.write("Incomplete user\n")
        return
        
    user_cache.add(user["_id"], user)
    user_cache.add(user["id"], user)
    if "username" in user:
        user_cache.add(user["username"], user)
    

def cache_users(users):
    for user in users:
        cache_user(user)


def cache_order(order):
    if not has_required_keys(order, "_id", "id", "mediaUrl", "createdAt", "status"):
        sys.stderr.write("Incomplete order\n")
        return
        
    order_cache.add(order["_id"], order)
    order_cache.add(order["id"], order)


def fetch_user(config, uid):
    user = api.run(config, "user", uid)
    cache_user(user)
    return user


def get_user(config, uid):
    user = user_cache.get(uid)
    if user is None:
        fetch_user(uid)
        return user_cache.get(uid)
    else:
        return user
        
        
def get_order(order_id):
    order = order_cache.get(order_id)
    if order is None:
        # todo: fetch
        return None
    else:
        return order
    

def get_userinfo_from_user(user):
    realname = user.get("name")
    username = user.get("username")
    uid = user["_id"]
    
    if username is None:
        if realname is not None:
            username = realname
        else:
            username = uid
            
    if realname is None:
        realname = username
        
    return {
        "realname": realname,
        "username": username,
        "uid": uid
    }


def get_userinfo_for_uid(uid, owner=None):
    if owner is None:
        owner = fetch_user(uid)
        
    if owner is None:
        return None

    return get_userinfo_from_user(owner)


def order_to_entry(order, entries=None):
    # /order/show
    if "order" in order:
        order = order["order"]
        
    cache_order(order)

    # _id instead of id because older orders use alternate IDs (which don't even match the video IDs)
    order_id = order["_id"]
    
    userinfo = get_userinfo_for_uid(order["ownerId"])
    
    extra = []
    extra.append("Celebrity: " + userinfo["realname"])
    
    if "purchaserName" in order:
        extra.append("Purchaser: " + order["purchaserName"])
        
    if "customerName" in order:
        extra.append("Customer: " + order["customerName"])
        
    if "instructions" in order:
        extra.append("Instructions: " + order["instructions"])
        
    if "likes" in order:
        extra.append("Likes: " + str(order["likes"]))
        
    image = order.get("nakedThumbnailUrl")
    if image is None:
        image = order["thumbnailUrl"]
        
    video = order.get("nakedMediaUrl")
    if video is None:
        video = order.get("mediaUrl")
    
    order_entry = {
        "caption": order_id,
        "url": "https://www.cameo.com/v/" + order_id,
        "extratext": "\n".join(extra),
        "author": userinfo["username"],
        "date": rssit.util.localize_datetime(datetime.datetime.fromtimestamp(snap["createdAt"])),
        "images": [],
        "videos": [{"image": image, "video": video}]
    }
    
    if entries is not None:
        duplicate = False
        for entry in entries:
            if entry["caption"] == order_entry["caption"]:
                duplicate = True
                break
                
        if not duplicate:
            entries.append(order_entry)
    
    return order_entry
    
    
def user_to_feed(user):
    userobj = user
    if "user" in userobj:
        userobj = userobj["user"]

    userinfo = get_userinfo_from_user(userobj)
    
    cache_user(userobj)
    if "bookingUsers" in user:
        cache_users(user["bookingUsers"])
    
    extra = []
    extra.append("Real name: %s" % userinfo["realname"])
    extra.append("Username: %s" % userinfo["username"])
    extra.append("UID: %s" % userinfo["uid"])

    if "profession" in userobj:
        extra.append("Profession: %s" % userobj["profession"])

    if "bio" in userobj:
        extra.append("Bio: %s" % userobj["bio"])
        
    price = userobj.get("price")
    if price is None:
        price = userobj.get("iosprice")
        
    if price is not None:
        extra.append("Price: $%s" % (price / 100))
        
    dmprice = userobj.get("dmprice")
    if dmprice is not None:
        extra.append("DM Price: $%s" % (dmprice / 100))

    if "averageMillisecondsToComplete" in userobj:
        extra.append("Average milliseconds to complete: %s" % userobj["averageMillisecondsToComplete"])
    
    entries = []
    entries.append({
        "caption": "[DP] " + re.sub("\\..*$", "", userobj["imageUrlKey"]),
        "url": userobj["imageUrl"],
        "date": rssit.util.parse_date(-1),
        "author": userinfo["username"],
        "images": [userobj["imageUrl"]],
        "videos": []
    })
    
    if "introOrder" in user:
        order_to_entry(user["introOrder"], entries)
        
    if "orders" in user:
        for order in user["orders"]:
            order_to_entry(order, entries)
            
    if "posts" in user:
        for order in user["posts"]:
            order_to_entry(order, entries)
            
    # todo: query
    
    return {
        "title": userinfo["realname"],
        "author": userinfo["username"],
        "description": "\n".join(extra),
        "url": "https://www.cameo.com/" + userinfo["uid"],
        "config": {
            "generator": "cameo"
        },
        "entries": entries
    }


def generate_user(config, uid):
    user = fetch_user(config, uid)
    if user is None:
        return
        
    feed = user_to_feed(user)
    if feed is None:
        return
        
    return ("social", feed)


infos = [{
    "name": "cameo",
    "display_name": "Cameo",

    "endpoints": {
        "u": {
            "name": "User's feed",
            "process": lambda server, config, path: generate_user(config, path)
        }
    },

    "config": {
    },

    "get_url": get_url,
}]
