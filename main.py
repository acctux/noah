#!/usr/bin/env python3
import outsidepy.usb_select as usb
import outsidepy.setup_disk as sd
import outsidepy.disk_format as df
import outsidepy.gather_necessary as gn
import outsidepy.misc as misc
from pathlib import Path
import subprocess
import logging
import re
import sys

# -------------------- CONFIG -------------------- #
FS_TYPES = ["ext4", "btrfs"]
MIN_SIZE = "20G"
EFI_DEFAULT = "512M"
ROOT_LABEL = "Arch"
MOUNT_OPTIONS = "noatime,compress=zstd"
BOOTLOADER = "systemd-boot"
INSTALL_SCRIPT = "noah"
KEY_DIR = ".ssh"
KEY_FILES = ["id_ed25519", "my-private-key.asc", "pass.asc"]
PKG_LISTS = ["business", "chaotic", "cli-tools", "coding", "dependencies"]
INSTALL_SCRIPT = "noah"
TIMEZONE = "US/Eastern"
HOST_NAME = "yulia"
USER_NAME = "nick"
LOCALE = "en_US.UTF-8"
ICON_GIT = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
KEYMAP = "us"

SCRIPT_DIR = Path(__file__).resolve().parent
PKG_D = Path(SCRIPT_DIR / "pkg")
COUNTRY_ISO = ""
SWORDPAS = ""

# ---------------- LOGGING ----------------
# Color mapping
COLORS = {
    "INFO": "\033[36m",  # cyan
    "SUCCESS": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "RESET": "\033[0m",
}


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"


log = logging.getLogger("keysync")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
log.addHandler(handler)


# --------------- UTILITIES ----------------
def chroot_run(cmd, check=False):
    """
    Run a command inside arch-chroot /mnt and stream its output live.
    """
    chroot_cmd = ["arch-chroot", "/mnt"] + cmd
    try:
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(chroot_cmd, text=True, check=check)
        log.info(f"Command finished with return code {result.returncode}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(cmd)}\nExit code: {e.returncode}")
        return e
    except OSError as e:
        log.error(f"OSError running command: {' '.join(cmd)}\n{e}")
        return None


def update_reflector(COUNTRY_ISO):
    """Update Pacman mirrorlist using reflector."""
    print("Updating reflector...")
    quantity = 15
    hours = 24
    seconds = 4
    cmd = [
        "reflector",
        f"--country={COUNTRY_ISO}",
        "--protocol=https",
        "--completion-percent=100",
        f"--age={hours}",
        f"--fastest={quantity}",
        "--sort=rate",
        "--threads=8",
        f"--download-timeout={seconds}",
        "--save=/etc/pacman.d/mirrorlist",
    ]

    try:
        subprocess.run(cmd, check=True)
        print("Mirrorlist updated successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error updating mirrorlist: {e}")


def run_or_fatal(cmd):
    """Run a shell command and exit on failure."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        log.error(f"{e}")
        sys.exit(1)


# --------------- OUTSIDE ENV SETUP ------------------
def outside_env():
    """
    Entry point for running disk setup interaction.
    """
    device_path = ""
    DEVICE = ""
    EFI_SIZE = ""
    print("=== Disk Setup Utility ===")

    COUNTRY_ISO, CPU_VENDOR, GPU_VENDOR = gn.get_necessary()
    log.info(f"Detected: {COUNTRY_ISO} {GPU_VENDOR} {CPU_VENDOR}")

    SWORDPAS = misc.ask_password()
    log.info(f"Your pass: {SWORDPAS}")
    usb.mnt_cp_keys(KEY_DIR, KEY_FILES)
    sd.umount_recursive()

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
    df.mount_install(EFI_PARTITION, ROOT_PARTITION, MOUNT_OPTIONS)

    update_reflector(COUNTRY_ISO)
    pacstrap_pkgs = ["base", "base-devel", "btrfs-progs", "linux", "linux-firmware"]
    misc.pacstrap_base(packages=pacstrap_pkgs)

    misc.generate_fstab()

    misc.write_secret_conf(
        BOOTLOADER,
        ROOT_PARTITION,
        SWORDPAS,
        CPU_VENDOR,
        GPU_VENDOR,
        COUNTRY_ISO,
    )
    misc.rsync_files_sys(INSTALL_SCRIPT, KEY_DIR)


# ----------- INSIDE ENV FUNCTIONS -------------
# ----------------------------------------
# 1. System locality configuration
# ----------------------------------------
def sys_locality(TIMEZONE, LOCALE, KEYMAP, HOST_NAME):
    log.info("Setting timezone, locale, and hostname...")
    chroot_run(
        ["ln", "-sf", f"/mnt/usr/share/zoneinfo/{TIMEZONE}", "/mnt/etc/localtime"]
    )
    chroot_run(["hwclock", "--systohc"])

    # Append locale to locale.gen
    locale_gen = Path("/mnt/etc/locale.gen")
    with locale_gen.open("a") as f:
        f.write(f"{LOCALE} UTF-8\n")

    chroot_run(["locale-gen"])

    Path("/mnt/etc/locale.conf").write_text(f"LANG={LOCALE}\n")
    Path("/mnt/etc/vconsole.conf").write_text(f"KEYMAP={KEYMAP}\n")
    Path("/mnt/etc/hostname").write_text(f"{HOST_NAME}\n")

    log.info("✅ System configuration completed successfully.")


# ----------------------------------------
# 2. Reflector + Regulatory Domain
# ----------------------------------------
def reflector_regdom_conf(COUNTRY_ISO):
    log.info("Writing reflector configuration...")

    Path("/mnt/etc/xdg/reflector").mkdir(parents=True, exist_ok=True)
    reflector_conf = Path("/mnt/etc/xdg/reflector/reflector.conf")
    reflector_conf.write_text(
        f"""--country "{COUNTRY_ISO}" \\
--protocol https \\
--completion-percent 100 \\
--age 18 \\
--fastest 15 \\
--sort rate \\
--threads 8 \\
--download-timeout 4 \\
--save /etc/pacman.d/mirrorlist
"""
    )

    log.info("✅ Reflector configuration updated successfully.")

    regdom_cfg = Path("/mnt/etc/modprobe.d/cfg80211.conf")
    regdom_cfg.write_text(f"options cfg80211 ieee80211_regdom={COUNTRY_ISO}\n")
    log.info(f"✅ Wireless regulatory domain set to {COUNTRY_ISO}.")


# ----------------------------------------
# 3. Chaotic-AUR Repository Setup
# ----------------------------------------
def chaotic_repo():
    log.info("Setting up Chaotic-AUR repository...")

    chaotic_key_id = "3056513887B78AEB"
    key_serv = "keyserver.ubuntu.com"

    chroot_run(["pacman-key", "--init"])
    chroot_run(["pacman-key", "--recv-key", chaotic_key_id, "--keyserver", key_serv])
    chroot_run(["pacman-key", "--lsign-key", chaotic_key_id])

    chroot_run(
        [
            "pacman",
            "-U",
            "--noconfirm",
            "--needed",
            "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst",
        ]
    )
    chroot_run(
        [
            "pacman",
            "-U",
            "--noconfirm",
            "--needed",
            "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst",
        ]
    )

    pacman_conf = Path("/mnt/etc/pacman.conf")
    with pacman_conf.open("a") as f:
        f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")

    log.info("✅ Chaotic-AUR repository added.")


# ----------------------------------------
# 4. pacman.conf tweaks
# ----------------------------------------
def s_pac_ed():
    pac_conf = Path("/mnt/etc/pacman.conf")
    text = pac_conf.read_text()

    # Uncomment "#Color"
    text = re.sub(r"^\s*#\s*Color\s*$", "Color", text, flags=re.MULTILINE)
    # Append "ILoveCandy" after "Color"
    text = re.sub(r"^\s*Color\s*$", "Color\nILoveCandy", text, flags=re.MULTILINE)

    # Uncomment "[multilib]" header
    text = re.sub(r"^\s*#\s*\[multilib\]", "[multilib]", text, flags=re.MULTILINE)
    # Uncomment "Include = ..." line under [multilib]
    text = re.sub(
        r"^\s*#\s*Include\s*=.*",
        lambda m: m.group(0).lstrip("# ").rstrip(),
        text,
        flags=re.MULTILINE,
    )

    # Replace ParallelDownloads line
    text = re.sub(
        r"^\s*ParallelDownloads.*$", "ParallelDownloads = 10", text, flags=re.MULTILINE
    )

    pac_conf.write_text(text)


# ----------------------------------------
# 5. Enable sudo insults
# ----------------------------------------
def enable_sudo_insults():
    sudoers = Path("/etc/sudoers").read_text()
    if "Defaults insults" not in sudoers:
        log.info("Enabling sudo insults...")
        new_text = sudoers.replace(
            "# Defaults!REBOOT !log_output",
            "# Defaults!REBOOT !log_output\nDefaults insults",
        )
        Path("/etc/sudoers").write_text(new_text)
        log.info("✅ Sudo insults enabled.")
    else:
        log.info("Insults already enabled, you masochist.")


# ----------------------------------------
# 6. Main execution
# ----------------------------------------
def etc_files_config():
    chaotic_repo()
    s_pac_ed()
    chroot_run(["pacman", "-Sy", "--noconfirm"], check=False)
    enable_sudo_insults()


def main():
    outside_env()
    chroot_run(
        [
            "pacman",
            "-Syu",
            "--noconfirm",
            "--needed",
            "pacman-contrib",
            "reflector",
            "rsync",
            "zsh-completions",
            "xdg-user-dirs",
        ]
    )
    sys_locality(TIMEZONE, LOCALE, KEYMAP, HOST_NAME)
    reflector_regdom_conf(COUNTRY_ISO)
    chaotic_repo()
    s_pac_ed()
    chroot_run(["pacman", "-Sy", "--noconfirm"], check=False)
    enable_sudo_insults()


main()
