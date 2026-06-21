from utils import run_dmc
from archinstall.lib.installer import Installer
from pathlib import Path


def modify_pacman_conf(
    mnt_point: Path | None, no_extracts: list[str] | None = None, value: int = 10
) -> None:
    no_extracts_line = "#NoExtract"
    if no_extracts:
        no_extracts_line = f"NoExtract = {' '.join(no_extracts)}"
    pacman_conf = (
        (mnt_point / "etc/pacman.conf") if mnt_point else Path("/etc/pacman.conf")
    )
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
        elif stripped.startswith(("#NoExtract", "NoExtract")):
            content[i] = no_extracts_line
        elif stripped == "[chaotic-aur]":
            del content[i : i + 2]
            continue
        elif stripped == "#[multilib]":
            content[i] = "[multilib]"
            content[i + 1] = content[i + 1].strip("#")
        i += 1
    with open(pacman_conf, "w") as pacman:
        pacman.write("\n".join(content) + "\n")


def chaotic_repo(installation: Installer | None) -> None:
    web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    keyring_cmds = [
        ["pacman-key", "--init"],
        [
            "pacman-key",
            "--recv-key",
            "3056513887B78AEB",
            "--keyserver",
            "keyserver.ubuntu.com",
        ],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    if installation:
        for cmd in keyring_cmds:
            installation.arch_chroot(" ".join(cmd))
        target_conf = installation.target / "etc/pacman.conf"
        with target_conf.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
        installation.arch_chroot("pacman -Sy")
    else:
        for cmd in keyring_cmds:
            run_dmc(cmd)
        with open("/etc/pacman.conf", "a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")
        run_dmc(["pacman", "-Sy"])
