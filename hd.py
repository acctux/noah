from archinstall.lib.models import SubvolumeModification
from pathlib import Path

from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.models.device import (
    DeviceModification,
    DiskEncryption,
    DiskLayoutConfiguration,
    DiskLayoutType,
    EncryptionType,
    FilesystemType,
    ModificationStatus,
    PartitionFlag,
    PartitionModification,
    PartitionType,
    Size,
    Unit,
)
from archinstall.lib.models.users import Password

device = device_handler.get_device(Path("/dev/vda"))
if not device:
    raise ValueError("No device found for given path")
device_modification = DeviceModification(device, wipe=True)
boot_partition = PartitionModification(
    status=ModificationStatus.CREATE,
    type=PartitionType.PRIMARY,
    start=Size(1, Unit.MiB, device.device_info.sector_size),
    length=Size(512, Unit.MiB, device.device_info.sector_size),
    mountpoint=Path("/boot"),
    fs_type=FilesystemType.FAT32,
    flags=[PartitionFlag.BOOT, PartitionFlag.ESP],
)
device_modification.add_partition(boot_partition)
start_home = boot_partition.length
length_home = device.device_info.total_size - start_home
home_partition = PartitionModification(
    status=ModificationStatus.CREATE,
    type=PartitionType.PRIMARY,
    start=start_home,
    length=length_home,
    mountpoint=None,
    fs_type=FilesystemType("btrfs"),
    btrfs_subvols=[
        SubvolumeModification(name="@", mountpoint=Path("/")),
        SubvolumeModification(name="@home", mountpoint=Path("/home")),
        SubvolumeModification(name="@log", mountpoint=Path("/var/log")),
        SubvolumeModification(name="@pkg", mountpoint=Path("/var/cache/pacman/pkg")),
    ],
    mount_options=["compress=zstd"],
)
device_modification.add_partition(home_partition)
disk_config = DiskLayoutConfiguration(
    config_type=DiskLayoutType.Default,
    device_modifications=[device_modification],
)
disk_encryption = DiskEncryption(
    encryption_password=Password(plaintext="pass"),
    encryption_type=EncryptionType.LUKS,
    partitions=[home_partition],
    hsm_device=None,
)
disk_config.disk_encryption = disk_encryption
d_conf = disk_config
