import asyncio
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType

DEVICE_PATH = "/org/bluez/hci0/dev_D8_AD_27_39_6D_00"
BLUEZ_SERVICE = "org.bluez"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"


async def main():
    try:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    except Exception as e:
        print(f"Failed to connect to system bus: {e}")
        return

    try:
        introspection = await bus.introspect(BLUEZ_SERVICE, DEVICE_PATH)
        device = bus.get_proxy_object(BLUEZ_SERVICE, DEVICE_PATH, introspection)
        props = device.get_interface(PROPERTIES_IFACE)

        address = await props.call_get("org.bluez.Device1", "Address")
        print(f"My variable is set to: {address.value}")

    except Exception as e:
        print(f"Failed to read device address: {e}")


if __name__ == "__main__":
    asyncio.run(main())
