#!/usr/bin/env python3
import scripts.setup_disk as sd
import scripts.disk_format as df
from scripts.my_log import log

# -------------------- Constants -------------------- #
FS_TYPES = ["ext4", "btrfs"]
MIN_SIZE = "20G"
EFI_DEFAULT = "512M"
ROOT_LABEL = "Arch"


def main():
    """
    Entry point for running disk setup interaction.
    """
    sd.umount_recursive()
    device_path = ""
    DEVICE = ""
    EFI_SIZE = ""
    print("=== Disk Setup Utility ===")
    try:
        EFI_SIZE = sd.ask_efi_size(EFI_DEFAULT)
        DEVICE = sd.prompt_user_selection(
            sd.find_install_partition(sd.get_lsblk_json())
        )
        device_path = f"/dev/{DEVICE}"
        log.info(f"{DEVICE} {EFI_SIZE} {device_path}")
    except KeyboardInterrupt:
        print("\nAborted by user.")
    except Exception as e:
        print(f"Error: {e}")

    df.check_disk(device_path)
    EFI_PARTITION, ROOT_PARTITION = df.set_partitions(device_path, EFI_SIZE)
    df.format_partitions(EFI_PARTITION, ROOT_PARTITION, ROOT_LABEL)


if __name__ == "__main__":
    main()
