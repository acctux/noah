#!/usr/bin/env python3
import subprocess
import logging
from pathlib import Path
import re

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Globals
TIMEZONE = "America/New_York"  # Example
LOCALE = "en_US.UTF-8"
HOST_NAME = "archbox"
ISO = "US"


def run(cmd, check=True):
    """Run a system command with logging."""
    log.info(f"→ Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {e}")
        if check:
            raise


# ----------------------------------------
# 1. System locality configuration
# ----------------------------------------
def sys_locality():
    log.info("Configuring system...")

    log.info("Setting timezone, locale, and hostname...")
    run(["ln", "-sf", f"/usr/share/zoneinfo/{TIMEZONE}", "/etc/localtime"])
    run(["hwclock", "--systohc"])

    # Append locale to locale.gen
    locale_gen = Path("/etc/locale.gen")
    with locale_gen.open("a") as f:
        f.write(f"{LOCALE} UTF-8\n")

    run(["locale-gen"])

    Path("/etc/locale.conf").write_text(f"LANG={LOCALE}\n")
    Path("/etc/vconsole.conf").write_text("KEYMAP=us\n")
    Path("/etc/hostname").write_text(f"{HOST_NAME}\n")

    log.info("✅ System configuration completed successfully.")


# ----------------------------------------
# 2. Reflector + Regulatory Domain
# ----------------------------------------
def reflector_regdom_conf():
    log.info("Writing reflector configuration...")

    Path("/etc/xdg/reflector").mkdir(parents=True, exist_ok=True)
    reflector_conf = Path("/etc/xdg/reflector/reflector.conf")
    reflector_conf.write_text(
        f"""--country "{ISO}" \\
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

    regdom_cfg = Path("/etc/modprobe.d/cfg80211.conf")
    regdom_cfg.write_text(f"options cfg80211 ieee80211_regdom={ISO}\n")
    log.info(f"✅ Wireless regulatory domain set to {ISO}.")


# ----------------------------------------
# 3. Chaotic-AUR Repository Setup
# ----------------------------------------
def chaotic_repo():
    log.info("Setting up Chaotic-AUR repository...")

    chaotic_key_id = "3056513887B78AEB"
    key_serv = "keyserver.ubuntu.com"

    run(["pacman-key", "--init"])
    run(["pacman-key", "--recv-key", chaotic_key_id, "--keyserver", key_serv])
    run(["pacman-key", "--lsign-key", chaotic_key_id])

    run(
        [
            "pacman",
            "-U",
            "--noconfirm",
            "--needed",
            "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst",
        ]
    )
    run(
        [
            "pacman",
            "-U",
            "--noconfirm",
            "--needed",
            "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst",
        ]
    )

    pacman_conf = Path("/etc/pacman.conf")
    with pacman_conf.open("a") as f:
        f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")

    log.info("✅ Chaotic-AUR repository added.")


# ----------------------------------------
# 4. pacman.conf tweaks
# ----------------------------------------
def s_pac_ed():
    pac_conf = Path("/etc/pacman.conf")
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
    run(["pacman", "-Sy", "--noconfirm"], check=False)
    enable_sudo_insults()
