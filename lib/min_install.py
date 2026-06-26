import time
from archinstall.lib.installer import Installer
from lib.datahandler import NoahConfig
import shutil
from utils import write_etc_file, run_dmc, copy_it
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


def chaotic_repo(installation: Installer) -> None:
    web = "https://cdn-mirror.chaotic.cx/chaotic-aur/"
    key_id = "3056513887B78AEB"
    cmds = [
        ["pacman-key", "--init"],
        ["pacman-key", "--recv-key", key_id, "--keyserver", "keyserver.ubuntu.com"],
        ["pacman-key", "--lsign-key", key_id],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-keyring.pkg.tar.zst"],
        ["pacman", "-U", "--noconfirm", f"{web}chaotic-mirrorlist.pkg.tar.zst"],
    ]
    for cmd in cmds:
        run_dmc(cmd)
        installation.arch_chroot(" ".join(cmd))
        time.sleep(1)
    repo_config = "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n"
    for path in [Path("/etc/pacman.conf"), installation.target / "etc/pacman.conf"]:
        if path.exists():
            content = path.read_text()
            if "[chaotic-aur]" not in content:
                with path.open("a") as f:
                    f.write(repo_config)
    sync_cmd = ["pacman", "-Sy"]
    run_dmc(sync_cmd)
    installation.arch_chroot(" ".join(sync_cmd))


def write_default_xdg_dirs(installation: Installer):
    user_dirs = {
        "DOCUMENTS": "Desktop/Documents",
        "DESKTOP": "Desktop",
        "MUSIC": "Desktop/Music",
        "PICTURES": "Desktop/Pictures",
        "BOOKS": "Desktop/Books",
        "SCREENSHOTS": "Desktop/Pictures/Screenshots",
        "GAMES": "Desktop/Games",
        "WALLPAPERS": "Desktop/Pictures/Wallpapers",
        "VIDEOS": "Desktop/Videos",
        "DOWNLOAD": "Desktop/Downloads",
        "TEMPLATES": "Desktop/Templates",
        "PRIVATE": "Desktop/Private",
        "PUBLICSHARE": "Desktop/Public",
        "PROJECTS": "Lit",
    }
    lines = [f"{k}={v}" for k, v in user_dirs.items()]
    write_etc_file(
        installation.target, {"etc/xdg/user-dirs.defaults": "\n".join(lines)}
    )


def min_intall_pre(nc: NoahConfig):
    handle_reflector(mountpoint=None, options=nc.reflector_options)
    modify_pacman_conf(mnt_point=None, no_extracts=nc.no_extracts)


def handle_reflector(mountpoint: Path | None, options: list[str] | None):
    if not options:
        options = [
            "--protocol https",
            "--latest 25",
            "--sort rate",
            "--number 3",
            "--save /etc/pacman.d/mirrorlist",
        ]
    if mountpoint:
        copy_it(
            Path("/etc/pacman.d/mirrorlist"), mountpoint / "etc/pacman.d/mirrorlist"
        )
        write_etc_file(
            mnt_point=mountpoint,
            files_to_write={"etc/xdg/reflector/reflector.conf": "\n".join(options)},
        )
    else:
        cmd = []
        for opt in options:
            for part in opt.split():
                cmd.append(part.strip())
        run_dmc(["reflector"] + cmd)


def copy_skel(mountpoint: Path, dots_git_user_repo: str):
    tmp = mountpoint / "tmp" / "tmp_skel"
    tmp.mkdir(exist_ok=True)
    git = f"https://github.com/{dots_git_user_repo}.git"
    run_dmc(["git", "clone", git, str(tmp)])
    shutil.rmtree(tmp / ".git")
    for p in tmp.iterdir():
        p.rename(p.parent / ("." + p.name))
    copy_it(tmp, mountpoint / "etc" / "skel")


def min_install_post(installation: Installer, nc: NoahConfig):
    handle_reflector(mountpoint=installation.target, options=nc.reflector_options)
    modify_pacman_conf(mnt_point=installation.target, no_extracts=nc.no_extracts)
    chaotic_repo(installation)
    if nc.dots_git_user_repo:
        copy_skel(
            mountpoint=installation.target,
            dots_git_user_repo=nc.dots_git_user_repo,
        )
    write_default_xdg_dirs(installation)
