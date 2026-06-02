from archinstall.lib.args import ArchConfig
from archinstall.lib.models.application import Firewall
from root_files import etc_files_to_write, network_files
import json
from lib.datahandler import NoahConfig
from utils import log, run_dmc, copy_it, write_etc_file
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
    if nc.dots_git_user_repo:
        tmp = mountpoint / "tmp" / "tmp_skel"
        tmp.mkdir(exist_ok=True)
        git = f"https://github.com/{nc.dots_git_user_repo}.git"
        run_dmc(["git", "clone", git, str(tmp)])
        shutil.rmtree(tmp / ".git")
        for p in tmp.iterdir():
            p.rename(p.parent / ("." + p.name))
        copy_it(tmp, mountpoint / "etc" / "skel")


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
        copy_it(source_dir, target_dir)


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


def replace_hosts_line(mnt_point: Path) -> None:
    new_hosts_line: str = "hosts: mymachines mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return] files myhostname dns"
    conf = mnt_point / "etc/nsswitch.conf"
    lines = conf.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("hosts"):
            lines[i] = new_hosts_line
            break
    conf.write_text("\n".join(lines) + "\n")


def write_reflector(
    installation: Installer,
    reflector_options: list[str],
):
    refl_conf = installation.target / "etc/xdg/reflector/reflector.conf"
    refl_conf.write_text("\n".join(reflector_options))


def replace_ly_config(mnt_point: Path) -> None:
    replacements = {
        "animation": "matrix",
        "bg": "0x00101013",
        "border_fg": "0x00D3DAE3",
        "cmatrix_fg": "0x000000FF",
        "colormix_col1": "0x0000FF00",
        "colormix_col2": "0x000000CC",
        "fg": "0x00D3DAE3",
        "numlock": "true",
        "session_log": ".cache/ly",
    }
    conf = Path(mnt_point / "etc/ly/config.ini")
    lines = conf.read_text().splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        for key, value in replacements.items():
            if stripped.startswith(f"{key}"):
                lines[i] = f"{key} = {value}"
                break
    conf.write_text("\n".join(lines) + "\n")


def handle_sys_files(
    installation: Installer,
    nc: NoahConfig,
    config: ArchConfig,
    script_d: Path,
):
    write_etc_file(installation.target, network_files)
    write_etc_file(installation.target, etc_files_to_write)
    replace_hosts_line(installation.target)
    replace_ly_config(installation.target)
    if nc.reflector_options:
        write_reflector(installation, nc.reflector_options)
    if nc.firefox_browser:
        set_extensions(installation.target, nc.firefox_browser)
    sys_dots(installation.target, script_d)
    install_icons(installation)
    handle_firewall(installation, config)
