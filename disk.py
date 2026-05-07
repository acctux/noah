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
from archinstall.lib.disk.device_handler import device_handler
from pathlib import Path


#########################
def create_disk_config():
    device_handler.load_devices()
    devices = device_handler.devices
    target_disk = ""
    for disk in devices:
        print(f"Checking disk: {disk.device_info.path}")
        for part in disk.partition_infos:
            if not part.fs_type:
                continue
            elif part.fs_type.name == "virtblk":
                target_disk = disk
                break
            elif part.fs_type.name == "FAT32":
                target_disk = disk
                break
            elif part.btrfs_subvol_infos != []:
                target_disk = disk
            print(f"Found partition: {part.path}")
    if not target_disk:
        print(devices)
        return
    device = device_handler.get_device(target_disk.device_info.path)
    if device:
        device_modification = DeviceModification(device, wipe=True)
        boot_partition = PartitionModification(
            status=ModificationStatus.CREATE,
            type=PartitionType.PRIMARY,
            start=Size(1, Unit.MiB, target_disk.device_info.sector_size),
            length=Size(512, Unit.MiB, target_disk.device_info.sector_size),
            mountpoint=Path("/boot"),
            fs_type=FilesystemType.FAT32,
            flags=[PartitionFlag.BOOT, PartitionFlag.ESP],
        )
        device_modification.add_partition(boot_partition)
        start_root = boot_partition.length
        length_root = device.device_info.total_size - start_root
        root_partition = PartitionModification(
            status=ModificationStatus.CREATE,
            type=PartitionType.PRIMARY,
            start=start_root,
            length=length_root,
            btrfs_subvols=[
                SubvolumeModification(Path("@"), Path("/")),
                SubvolumeModification(Path("@home"), Path("/home")),
            ],
            flags=[],
            mountpoint=None,
            mount_options=["compress=zstd"],
            fs_type=FilesystemType("btrfs"),
        )
        device_modification.add_partition(root_partition)
        return DiskLayoutConfiguration(
            config_type=DiskLayoutType.Default,
            device_modifications=[device_modification],
        )


k = create_disk_config()
print(k)
