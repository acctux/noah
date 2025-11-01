#!/usr/bin/env python3

import subprocess
from pyutils.my_log import log
import sys


def update_reflector(iso, quantity=15, hours=24, seconds=4):
    """Update Pacman mirrorlist using reflector."""
    print("Updating reflector...")

    cmd = [
        "reflector",
        f"--country={iso}",
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
