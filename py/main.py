#!/usr/bin/env python3
import scripts.setup_disk as sd
import scripts.disk_format as df
from scripts.my_log import log

# -------------------- Constants -------------------- #
FS_TYPES = ["ext4", "btrfs"]
MIN_SIZE = "20G"
EFI_DEFAULT = "512M"


def main():
    """
    Entry point for running disk setup interaction.
    """
    device_path = ""
    print("=== Disk Setup Utility ===")
    try:
        EFI_SIZE = sd.ask_efi_size()
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


if __name__ == "__main__":
    main()
