#!/usr/bin/env python3
import asyncio
import os
import sys
from dbus_fast.aio import MessageBus


async def main():
    if os.path.exists("/var/lib/pacman/db.lck"):
        return
    msg = sys.argv[1] if len(sys.argv) > 1 else "Power event"
    bus = await MessageBus().connect()
    introspection = await bus.introspect(
        "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
    )
    obj = bus.get_proxy_object(
        "org.freedesktop.Notifications", "/org/freedesktop/Notifications", introspection
    )
    notify = obj.get_interface("org.freedesktop.Notifications")
    await notify.call_notify(  # type: ignore
        "power-notify",  # app_name
        0,  # replaces_id
        "/usr/share/icons/WhiteSur-dark/devices/scalable/battery.svg",  # app_icon
        "Power Event",  # summary/title
        msg,  # detailed body
        [],  # actions
        {},  # hints
        5000,  # timeout in ms (longer to read details)
    )


asyncio.run(main())
