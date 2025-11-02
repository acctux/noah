#!/usr/bin/env python3
import logging
from pathlib import Path
from main import chroot_run as chroot
from main import COUNTRY_ISO
import re

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Globals
TIMEZONE = "America/New_York"  # Example
LOCALE = "en_US.UTF-8"
HOST_NAME = "archbox"
ISO = "US"


# ----------------------------------------
# 1. System locality configuration
# ----------------------------------------
def sys_locality():
    log.info("Configuring system...")

    log.info("Setting timezone, locale, and hostname...")
    chroot(["ln", "-sf", f"/mnt/usr/share/zoneinfo/{TIMEZONE}", "/mnt/etc/localtime"])
    chroot(["hwclock", "--systohc"])

    # Append locale to locale.gen
    locale_gen = Path("/mnt/etc/locale.gen")
    with locale_gen.open("a") as f:
        f.write(f"{LOCALE} UTF-8\n")

    chroot(["locale-gen"])

    Path("/mnt/etc/locale.conf").write_text(f"LANG={LOCALE}\n")
    Path("/mnt/etc/vconsole.conf").write_text("KEYMAP=us\n")
    Path("/mnt/etc/hostname").write_text(f"{HOST_NAME}\n")

    log.info("✅ System configuration completed successfully.")


# ----------------------------------------
# 2. Reflector + Regulatory Domain
# ----------------------------------------
def reflector_regdom_conf():
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

    chroot(["pacman-key", "--init"])
    chroot(["pacman-key", "--recv-key", chaotic_key_id, "--keyserver", key_serv])
    chroot(["pacman-key", "--lsign-key", chaotic_key_id])

    chroot(
        [
            "pacman",
            "-U",
            "--noconfirm",
            "--needed",
            "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst",
        ]
    )
    chroot(
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
    sys_locality()
    reflector_regdom_conf()
    chaotic_repo()
    s_pac_ed()
    chroot(["pacman", "-Sy", "--noconfirm"], check=False)
    enable_sudo_insults()
