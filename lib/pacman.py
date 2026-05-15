import time
from utils import run_dmc
from archinstall.lib.installer import Installer
from pathlib import Path


def modify_pacman_conf(
    mnt_point: Path | None, no_extracts: list[str], value: int = 10
) -> None:
    pacman_conf = "/etc/pacman.conf"
    if mnt_point:
        pacman_conf = mnt_point / "etc/pacman.conf"
    with open(pacman_conf) as pacman:
        content = pacman.read().splitlines()
    i = 0
    while i < len(content):
        stripped = content[i].strip()
        if stripped.startswith("ParallelDownloads"):
            content[i] = f"ParallelDownloads = {value}"
        elif stripped in ("#Color", "Color"):
            content[i] = "Color"
            if content[i + 1] != "ILoveCandy":
                content.insert(i + 1, "ILoveCandy")
        elif stripped.startswith("#NoExtract") or stripped.startswith("NoExtract"):
            content[i] = f"NoExtract = {' '.join(no_extracts)}"
        elif stripped == "[chaotic-aur]":
            del content[i : i + 2]
            continue  # maintain same index
        i += 1
    with open(pacman_conf, "w") as pacman:
        pacman.write("\n".join(content) + "\n")


def chaotic_repo(installation: Installer) -> None:
    web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds = [
        [
            "pacman-key",
            "--recv-key",
            "3056513887B78AEB",
            "--keyserver",
            "keyserver.ubuntu.com",
        ],
        # ["pacman-key", "--add", "/root/chaotic.key"],
        ["pacman-key", "--lsign-key", "3056513887B78AEB"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    cmd = ["pacman-key", "--init"]
    run_dmc(cmd)
    installation.arch_chroot(" ".join(cmd))
    time.sleep(1)
    cmd = [
        "pacman-key",
        "--recv-key",
        "3056513887B78AEB",
        "--keyserver",
        "keyserver.ubuntu.com",
    ]
    if not run_dmc(cmd):
        cmd = ["pacman-key", "--add", "/root/chaotic.key"]
        run_dmc(cmd)
    if not installation.arch_chroot(" ".join(cmd)):
        cmd = ["pacman-key", "--add", "/root/chaotic.key"]
        installation.arch_chroot(" ".join(cmd))
    time.sleep(1)
    for cmd in cmds:
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
        time.sleep(1)
    for path in [Path("/etc/pacman.conf"), installation.target / "etc/pacman.conf"]:
        with path.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
            time.sleep(1)
    run_dmc(["pacman", "-Sy"], check=True)
    installation.arch_chroot("pacman -Sy")
