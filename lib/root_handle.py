from archinstall.lib.args import ArchConfig
from archinstall.lib.models.application import Firewall
from root_files import etc_files_to_write
import json
from lib.datahandler import NoahConfig
from utils import log, run_dmc, copy_dir, write_etc_file
import shutil
from archinstall.lib.installer import Installer
from pathlib import Path


def install_icons(installation: Installer):
    git = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
    installation.arch_chroot(f"git clone {git}")
    installation.arch_chroot("bash ./WhiteSur-icon-theme/install.sh")
    installation.arch_chroot("rm -rf ./WhiteSur-icon-theme")
    icon_path = installation.target / "usr/share/icons"
    white_sur_light = icon_path / "WhiteSur-light"
    if white_sur_light.exists():
        shutil.rmtree(white_sur_light)
        log.info(f"Removed {white_sur_light}")
    themes_to_modify = []
    for folder in icon_path.iterdir():
        if folder.is_dir() and ("-dark" in folder.name or "WhiteSur" in folder.name):
            themes_to_modify.append(folder)
    for theme_dir in themes_to_modify:
        for svg_file in theme_dir.rglob("*.svg"):
            if svg_file.is_file():
                text = svg_file.read_text()
                if "#ffffff" in text:
                    svg_file.write_text(text.replace("#ffffff", "#F4F5F6"))
                    log.info(f"Modified {svg_file}")


def copy_skel(mountpoint: Path, nc: NoahConfig):
    if nc.dots_repo:
        tmp = mountpoint / "tmp" / nc.dots_repo
        tmp.mkdir(exist_ok=True)
        git = f"https://github.com/{nc.git_user}/{nc.dots_repo}.git"
        run_dmc(["git", "clone", git, str(tmp)])
        shutil.rmtree(tmp / ".git")
        for p in tmp.iterdir():
            p.rename(p.parent / ("." + p.name))
        copy_dir(tmp, mountpoint / "etc" / "skel")


def set_extensions(
    mnt_point: Path,
    browser: str,
    extension_ids: list[str] = [
        "return-youtube-dislikes",
        "leechblock-ng",
        "proton-pass",
        "firefox-color",
        "darkreader",
        "flagfox",
        "ublock-origin",
    ],
) -> None:
    """Set Firefox extensions from a list of extension IDs."""
    new_install = [
        f"https://addons.mozilla.org/firefox/downloads/latest/{ext}/latest.xpi"
        for ext in extension_ids
    ]
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    data = {}
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text())
        except json.JSONDecodeError:
            log.warning(f"Corrupt JSON in {file_path}, resetting.")
    policies = data.setdefault("policies", {})
    extensions = policies.setdefault("Extensions", {})
    extensions["Install"] = new_install
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2))
    log.info(f"'Extensions.Install' for {browser} has been overwritten.")


def sys_dots(
    mnt_point: Path,
    script_dir: Path,
    dirs_to_cp: list[str] = ["etc", "usr"],
) -> None:
    for dir_name in dirs_to_cp:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        log.info("Processing %s -> %s", source_dir, target_dir)
        if not source_dir.exists():
            log.error("Source directory not found: %s", source_dir)
            continue
        shutil.copytree(
            source_dir,
            target_dir,
            dirs_exist_ok=True,
            copy_function=shutil.copy2,
        )
        log.info("Copied %s to %s", source_dir, target_dir)


def handle_firewall(
    installation: Installer,
    config: ArchConfig,
    ports_to_open: list[str] = ["KDEConnect", "Deluge", "51820/udp"],
):
    if app_config := config.app_config:
        if firewall_conf := app_config.firewall_config:
            if firewall_conf.firewall == Firewall("ufw"):
                for allow_port in ports_to_open:
                    installation.arch_chroot(f"ufw allow {allow_port}")


def handle_sys_files(
    installation: Installer,
    nc: NoahConfig,
    config: ArchConfig,
    script_d: Path,
):
    write_etc_file(installation.target, etc_files_to_write)
    if nc.reflector_country:
        reflector_options = [
            f"--country {nc.reflector_country}",
            "--protocol https",
            "--latest 15",
            "--sort rate",
            "--number 3",
            "--save /etc/pacman.d/mirrorlist",
        ]
        (installation.target / "etc/xdg/reflector/reflector.conf").write_text(
            "\n".join(reflector_options)
        )
    if nc.firefox_browser:
        set_extensions(installation.target, nc.firefox_browser)
    sys_dots(installation.target, script_d)
    install_icons(installation)
    handle_firewall(installation, config)
