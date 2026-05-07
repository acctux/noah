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
    SubvolumeModification,
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


def find_disk_with_fs(devices, primary_fs="FAT32", fallback_fs="BTRFS"):
    """Find a disk containing primary_fs, otherwise fallback_fs."""
    fat32_disk = None
    btrfs_disk = None

    for disk in devices:
        print(f"Checking disk: {disk.device_info.path}")
        for part in disk.partition_infos:
            if part.fs_type:
                if part.fs_type.name == primary_fs:
                    print(f"Found {primary_fs} partition: {part.path}")
                    fat32_disk = disk.device_info.path
                    break
                elif part.fs_type.name == fallback_fs and btrfs_disk is None:
                    btrfs_disk = disk.device_info.path

        if fat32_disk:
            return fat32_disk
    if btrfs_disk:
        print(
            f"No {primary_fs} partition found, using {fallback_fs} disk: {btrfs_disk}"
        )
        return btrfs_disk
    print(f"No {primary_fs} or {fallback_fs} partitions found on any disk.")
    return None


fat32_disk = find_disk_with_fs(devices)

device = device_handler.get_device(fat32_disk)

if not device:
    raise ValueError("No device found for given path")
print(device)
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
    fs_type=fs_type,
    mountpoint=Path("/home"),
    mount_options=[],
    flags=[],
    btrfs_subvols=[
        SubvolumeModification(Path("@"), Path("/")),
        SubvolumeModification(Path("@home"), Path("/home")),
    ],
)
device_modification.add_partition(home_partition)
disk_config = DiskLayoutConfiguration(
    config_type=DiskLayoutType.Default,
    device_modifications=[device_modification],
)
