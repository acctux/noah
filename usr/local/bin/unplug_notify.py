#!/usr/bin/env python3
import asyncio
import os
import pwd
import subprocess
import sys

from dbus_fast import Message
from dbus_fast.aio import MessageBus


async def main():
    if os.path.exists("/var/lib/pacman/db.lck"):
        sys.exit(0)
    msg = sys.argv[1] if len(sys.argv) > 1 else "Power event"
    user = subprocess.check_output(
        ["loginctl", "list-sessions", "--no-legend"],
        text=True,
    ).split()[2]
    pw = pwd.getpwnam(user)
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)
    bus = await MessageBus(bus_address=f"unix:path=/run/user/{pw.pw_uid}/bus").connect()
    await bus.call(
        Message(
            destination="org.freedesktop.Notifications",
            path="/org/freedesktop/Notifications",
            interface="org.freedesktop.Notifications",
            member="Notify",
            signature="susssasa{sv}i",
            body=[
                "power-notify",
                0,
                "",
                "Power",
                msg,
                [],
                {},
                3000,
            ],
        )
    )


asyncio.run(main())
