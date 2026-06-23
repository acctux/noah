#!/usr/bin/env python3

import asyncio
from dbus_fast.aio import MessageBus
from dbus_fast import BusType, Message
from pathlib import Path
import subprocess
import time
from systemd import journal

MOUSE_NAME = "MX Master 3S"


def run_cmd(cmd: list[str], check=False) -> str:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    ).stdout.strip()


def find_device_mac(name: str, mac_file: Path) -> None:
    data = run_cmd(["bluetoothctl", "devices"])
    mac_id = ""
    for line in data.splitlines():
        if name in line:
            mac_id = line.split()[1].upper().replace(":", "_")
            print(f"Found MAC: {mac_id}")
            break
    if mac_id:
        mac_file.write_text(mac_id + "\n")
        print(f"MAC saved to {mac_file}")
    else:
        print(f"No device named '{name}' found.")


def logid_failed() -> bool:
    for entry in (
        journal.Reader()
        .add_match(_SYSTEMD_UNIT="logid.service")
        .seek_tail()
        .get_previous(2)
    ):
        message = entry.get("MESSAGE", "")
        if "[WARN] Failed" in message:
            print(f"Warning detected in logs: {message}")
            return True
    return False


def restart_logid(flag_file: Path) -> None:
    def logid_restart() -> None:
        run_cmd(["sudo", "systemctl", "stop", "logid.service"])
        time.sleep(1)
        run_cmd(["sudo", "systemctl", "start", "logid.service"])

    logid_restart()
    time.sleep(3)
    flag_file.touch()
    time.sleep(10)
    if logid_failed():
        print("Warning still in logs after restart! Retrying")
        logid_restart()
    else:
        print("No warnings detected in logs after restart.")


async def get_device_property(prop: str, device_path: str) -> str:
    try:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        reply = await bus.call(
            Message(
                destination="org.bluez",
                path=device_path,
                interface="org.freedesktop.DBus.Properties",
                member="Get",
                signature="ss",
                body=["org.bluez.Device1", prop],
            )
        )
        bus.disconnect()
        val = reply.body[0]
        return val.value if hasattr(val, "value") else val
    except Exception as e:
        print(f"Error reading {prop}: {e}")
        return ""


def handle_signal(msg: Message, device_path: str, flag_file: Path) -> None:
    if msg.path != device_path:
        return
    if msg.member != "PropertiesChanged" or len(msg.body) < 2:
        return
    if msg.body[0] != "org.bluez.Device1":
        return
    if "ServicesResolved" not in msg.body[1]:
        return
    val = msg.body[1]["ServicesResolved"]
    if hasattr(val, "value"):
        val = val.value
    if val is True:
        print("ServicesResolved = True → Triggering logid_nuclear")
        restart_logid(flag_file)


async def add_match(bus: MessageBus, rule: str) -> None:
    await bus.call(
        Message(
            destination="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="AddMatch",
            signature="s",
            body=[rule],
        )
    )


async def main():
    flag_file = Path("/tmp/mouse_connected.flag")
    logi_mac_file = Path("/") / "usr" / "local" / "bin" / "logi_mouse_mac"
    if not logi_mac_file.is_file():
        find_device_mac(MOUSE_NAME, logi_mac_file)
    if logi_mac_file.is_file():
        dev_path = f"/org/bluez/hci0/dev_{logi_mac_file.read_text().strip()}"
        connected = await get_device_property("Connected", dev_path)
        resolved = await get_device_property("ServicesResolved", dev_path)
        if connected and resolved:
            print("Mouse already fully connected on startup → running logid_nuclear")
            restart_logid(flag_file)
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        bus.add_message_handler(lambda msg: handle_signal(msg, dev_path, flag_file))
        await add_match(
            bus,
            "type='signal',interface='org.freedesktop.DBus.Properties',member='PropertiesChanged',arg0='org.bluez.Device1'",
        )
        print(f"Monitoring {dev_path} for ServicesResolved...")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
