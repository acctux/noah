from pathlib import Path
import textwrap
from noah_lib.sys_functions import run_cc
from noah_lib.utils import get_logger, run_cmd

log = get_logger("Noah")


def chaotic_repo(mnt_point: Path | None = None):
    log.info("Setting up Chaotic-AUR repository.")
    chaotic_key_id = "3056513887B78AEB"
    key_serv = "keyserver.ubuntu.com"
    chaotic_web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    cmds_setup = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", chaotic_key_id, "--keyserver", key_serv],
        ["pacman-key", "--lsign-key", chaotic_key_id],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{chaotic_web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    cmds_update = ["pacman", "-Sy"]
    if mnt_point:
        for cmd in cmds_setup:
            run_cc([" ".join(cmd)], mnt_point)
        pacman_conf = mnt_point / "etc/pacman.conf"
        run_cc([" ".join(cmds_update)], mnt_point)
    else:
        for cmd in cmds_setup:
            run_cmd(cmd, check=True)
        pacman_conf = Path("/etc/pacman.conf")
        run_cmd(cmds_update, check=True)
    section = "[chaotic-aur]"
    content = pacman_conf.read_text()
    if section not in content:
        with pacman_conf.open("a") as f:
            f.write("\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n")


def config_pac_conf(mnt_point: Path | None = None, parallel_downloads: int = 10):
    pacman_content = textwrap.dedent(f"""\
        [options]
        HoldPkg     = pacman glibc
        Architecture = auto
        Color
        ILoveCandy
        ParallelDownloads = {parallel_downloads}
        DownloadUser = alpm
        SigLevel    = Required DatabaseOptional
        LocalFileSigLevel = Optional
        NoExtract = /etc/xdg/autostart/firewall-applet.desktop
        NoExtract = /usr/share/icons/capitaine-cursors/*

        [core]
        Include = /etc/pacman.d/mirrorlist

        [extra]
        Include = /etc/pacman.d/mirrorlist

        [multilib]
        Include = /etc/pacman.d/mirrorlist
    """)
    pacman_conf_path = Path("/etc/pacman.conf")
    if mnt_point:
        pacman_conf_path = mnt_point / "etc/pacman.conf"
    pacman_conf_path.write_text(pacman_content.strip())
    if mnt_point:
        run_cc(["pacman -Sy"], mnt_point)
    else:
        run_cmd(["pacman", "-Sy"], True)
