import dbus
import dbus.service
import dbus.mainloop.glib
import rssit.util
import rssit.persistent
import threading
import datetime
import os
import signal


notifications = rssit.util.Cache("notifications", 24*60*60, 0)
notification_entries = rssit.util.Cache("notification_entries", 24*60*60, 0)


def process_notification(notification):
    notifications.add(notification["notification_id"], notification)
    notification_entries.add(notification["notification_id"], {
        "title": notification["summary"] or "(n/a)",
        "content": notification["body"] or "(n/a)",
        "url": notification["url"],
        "author": notification["app_name"],
        "date": notification["date"]
    })


def create_guid(date, notification_id):
    return str(date) + "_" + str(notification_id)


# adapted from https://github.com/halhen/statnot/blob/master/statnot
class NotificationFetcher(dbus.service.Object):
    _id = 0

    def __init__(self):
        bus = dbus.SessionBus()
        bus.request_name("org.freedesktop.Notifications")
        bus_name = dbus.service.BusName("org.freedesktop.Notifications", bus=bus)
        dbus.service.Object.__init__(self, bus_name, '/org/freedesktop/Notifications')

    @dbus.service.method("org.freedesktop.Notifications",
                         in_signature='susssasa{ss}i',
                         out_signature='u')
    def Notify(self, app_name, notification_id, app_icon,
               summary, body, actions, hints, expire_timeout):
        self._id += 1
        #date = rssit.util.localize_datetime(datetime.datetime.now())
        date = datetime.datetime.now().timestamp()
        if not notification_id:
            notification_id = self._id
            notification_guid = create_guid(date, notification_id)
        else:
            pre_notification = notifications.get(notification_id)
            if not pre_notification:
                notification_guid = create_guid(date, notification_id)
            else:
                notification_guid = pre_notification["notification_guid"]
                date = pre_notification["date"]

        url = rssit.util.get_local_url("/f/notifications/id/" + notification_guid)
        notification = {
            "app_name": app_name,
            "notification_id": notification_id,
            "notification_guid": notification_guid,
            "url": url,
            "date": date,
            "app_icon": app_icon,
            "summary": summary,
            "body": body,
            "actions": actions,
            "hints": hints,
            "expire_timeout": expire_timeout
        }
        process_notification(notification)

        return notification_id

    @dbus.service.method("org.freedesktop.Notifications", in_signature='', out_signature='as')
    def GetCapabilities(self):
        return ("body", "body-hyperlinks", "body-images", "body-markup", "persistence")

    @dbus.service.signal('org.freedesktop.Notifications', signature='uu')
    def NotificationClosed(self, id_in, reason_in):
        pass

    @dbus.service.method("org.freedesktop.Notifications", in_signature='u', out_signature='')
    def CloseNotification(self, id):
        pass

    @dbus.service.method("org.freedesktop.Notifications", in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ("rssit", "https://github.com/qsniyg/rssit", "0.0.1", "1")


def run_gobject_thread():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    rssit.persistent.storage["notification_fetcher"] = NotificationFetcher()
    rssit.util.gobject.threads_init()
    #rssit.util.glib.idle_add(install_glib_handler, signal.SIGINT, priority=GLib.PRIORITY_HIGH)
    rssit.persistent.storage["mainloop"] = rssit.util.gobject.MainLoop()
    try:
        rssit.persistent.storage["mainloop"].run()
    except KeyboardInterrupt:
        os.kill(os.getpid(), signal.SIGTERM)


def init(config):
    if "notifications_server" not in config or not config["notifications_server"]:
        return
    gobject_thread = threading.Thread(target=run_gobject_thread)
    gobject_thread.start()


def unload(config):
    if "mainloop" in rssit.persistent.storage:
        rssit.persistent.storage["mainloop"].quit()


def generate_feed(server, config, path):
    feed = {
        "title": "Notifications",
        "description": "Desktop notifications",
        "url": rssit.util.get_local_url("/f/notifications"),
        "author": "rssit",
        "entries": []
    }

    entries = notification_entries.get_all()
    for entry_id in entries:
        entries[entry_id]["date"] = rssit.util.localize_datetime(datetime.datetime.fromtimestamp(entries[entry_id]["date"], None))
        feed["entries"].append(entries[entry_id])
    return ("feed", feed)


infos = [{
    "name": "notifications",
    "display_name": "Notifications",

    "init": init,
    "unload": unload,

    "endpoints": {
        "feed": {
            "name": "Feed",
            "process": generate_feed
        }
    },

    "config": {
        "notifications_server": {
            "name": "Create DBUS Server",
            "description": "Create DBUS server for notifications. If set to false, no notifications will be recorded",
            "value": False
        }
    }
}]
