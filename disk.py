#!/usr/bin/env python3
from archinstall.lib.models import (
    DeviceModification,
    PartitionModification,
    ModificationStatus,
    PartitionType,
    Unit,
    Size,
    FilesystemType,
    PartitionFlag,
    DiskLayoutConfiguration,
    DiskLayoutType,
)
import logging
from archinstall.lib.disk.device_handler import device_handler
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Get all devices from archinstall
devices = device_handler.devices
print(devices)
fs_type = FilesystemType("ext4")


def find_disk_with_fat32(devices):
    if not devices:
        return
    for disk in devices:
        print(f"Checking disk: {disk.device_info.path}")
        if "sda" in str(disk.device_info.path):
            return
        for part in disk.partition_infos:
            if part.fs_type.name == "FAT32":
                print(f"Found FAT32 partition: {part.path}")
                return disk.device_info.path
    return None


fat32_disk = find_disk_with_fat32(devices)

device = device_handler.get_device(fat32_disk)

if not device:
    raise ValueError("No device found for given path")

# create a new modification for the specific device
device_modification = DeviceModification(device, wipe=True)

boot_partition = PartitionModification(
    status=ModificationStatus.CREATE,
    type=PartitionType.PRIMARY,
    start=Size(1, Unit.MiB, device.device_info.sector_size),
    length=Size(512, Unit.MiB, device.device_info.sector_size),
    mountpoint=Path("/boot"),
    fs_type=FilesystemType.FAT32,
    flags=[PartitionFlag.BOOT],
)
device_modification.add_partition(boot_partition)
# create a root partition
root_partition = PartitionModification(
    status=ModificationStatus.CREATE,
    type=PartitionType.PRIMARY,
    start=Size(513, Unit.MiB, device.device_info.sector_size),
    length=Size(20, Unit.GiB, device.device_info.sector_size),
    mountpoint=None,
    fs_type=fs_type,
    mount_options=[],
)
device_modification.add_partition(root_partition)

start_home = root_partition.length
length_home = device.device_info.total_size - start_home
# create a new home partition
home_partition = PartitionModification(
    status=ModificationStatus.CREATE,
    type=PartitionType.PRIMARY,
    start=start_home,
    length=length_home,
    mountpoint=Path("/home"),
    fs_type=fs_type,
    mount_options=[],
)
device_modification.add_partition(home_partition)
disk_config = DiskLayoutConfiguration(
    config_type=DiskLayoutType.Default,
    device_modifications=[device_modification],
)
print(disk_config)
