from pathlib import Path
from textwrap import dedent
from archinstall.lib.args import ArchConfig
from archinstall.lib.installer import Installer
from archinstall.lib.models import Bootloader
from utils import copy_it, log, write_etc_file, modify_mkinit


# ==============================================================================
# 1. LIMINE CONFIGURATION
# ==============================================================================
def write_limine_opt(
    installation: Installer, filename: str, kernel_params: str, run_refresh: bool = True
) -> None:
    target = installation.target / "etc" / "limine-entry-tool.d" / f"{filename}.conf"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"KERNEL_CMDLINE[default]+={kernel_params}\n", encoding="utf-8")
    log.info(f"Wrote extra option '{kernel_params}' to {target}")
    if run_refresh:
        installation.arch_chroot("limine-mkinitcpio")


def get_cmdline(mountpoint: Path) -> str:
    limine_conf = mountpoint / "boot" / "EFI" / "arch-limine" / "limine.conf"
    if not limine_conf.exists():
        log.warning(f"Limine configuration file not found at {limine_conf}")
        return ""
    for line in limine_conf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("cmdline:"):
            cmdline = line.split(":", 1)[1].strip()
            log.info(f"Retrieved cmdline: {cmdline}")
            return cmdline
    return ""


def write_limine_conf(mountpoint: Path) -> None:
    limine_conf = mountpoint / "boot" / "limine.conf"
    if not limine_conf.exists():
        log.warning(f"Limine configuration file not found at {limine_conf}")
        return
    theme = [
        "interface_branding:",
        "term_palette: 21222c;ff5555;00ff99;f1fa8c;0072ff;ff79c6;33ccff;bfbfbf",
        "term_palette_bright: 4d4d4d;ff6e6e;10b981;ffffa5;a5b4fc;ff92df;a4ffff;ffffff",
        "term_background: 101013",
        "term_foreground: f4f5f6",
        "term_background_bright: 4d4d4d",
        "term_foreground_bright: white",
        "interface_branding_color: 0072ff",
        "interface_help_color: 0072ff",
        "interface_help_color_bright: a5b4fc",
    ]
    new_lines = []
    for line in limine_conf.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("timeout:"):
            new_lines.extend(["timeout: 1", "remember_last_entry: yes"])
            continue
        new_lines.append(line)
        if line.strip() == "### Theme":
            new_lines.extend(theme)
    limine_conf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    log.info(f"Updated config parameters inside {limine_conf}")


def set_target_os(mnt: Path, target_os: str) -> None:
    default_limine = mnt / "etc" / "default" / "limine"
    copy_it(mnt / "etc" / "limine-entry-tool.conf", default_limine)
    if not default_limine.exists():
        return
    updates = {
        "TARGET_OS_NAME": f"'{target_os}'",
        "FIND_BOOTLOADERS": "no",
        "ESP_PATH": "/boot",
    }
    lines = default_limine.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        left_side, separator, _ = line.partition("=")
        key = left_side.strip().lstrip("#").strip()
        if separator and key in updates:
            new_lines.append(f"{key}={updates[key]}")
        else:
            new_lines.append(line)
    for key, value in updates.items():
        if key not in [
            line.split("=")[0].strip().lstrip("#").strip()
            for line in lines
            if "=" in line
        ]:
            new_lines.append(f"{key}={value}")
    default_limine.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def install_limine(installation: Installer) -> None:
    installation.add_additional_packages("limine-mkinitcpio-hook")
    write_limine_conf(installation.target)
    set_target_os(installation.target, target_os="Arch Linux")
    cmdline = get_cmdline(installation.target)
    write_limine_opt(installation, "original_flags", cmdline, run_refresh=False)


# ==============================================================================
# 2. SUBSYSTEM MODULES
# ==============================================================================
def inst_apparmor(installation: Installer) -> None:
    installation.add_additional_packages(["apparmor", "apparmor.d-git"])
    write_limine_opt(
        installation,
        "apparmor",
        "lsm=landlock,lockdown,yama,integrity,apparmor,bpf",
        run_refresh=False,
    )
    content = {
        "etc/apparmor/parser.conf": dedent(
            """\
            write-cache
            cache-loc /etc/apparmor/earlypolicy/
            """
        )
    }
    write_etc_file(installation.target, content)
    installation.enable_service("apparmor")


def inst_plymouth(installation: Installer) -> None:
    installation.add_additional_packages("plymouth")
    write_limine_opt(
        installation,
        filename="plymouth",
        kernel_params="quiet splash",
        run_refresh=False,
    )
    modify_mkinit(installation.target, hook="plymouth", after_hook="kms")


# ==============================================================================
# 3. MAIN HANDLING
# ==============================================================================
def bootloader_handling(installation: Installer, config: ArchConfig) -> None:
    boot_conf = config.bootloader_config
    if boot_conf and boot_conf.bootloader == Bootloader.Limine and not boot_conf.uki:
        install_limine(installation)
        inst_apparmor(installation)
        inst_plymouth(installation)
        log.info("Refreshing limine-mkinitcpio hooks cleanly.")
        installation.arch_chroot("limine-mkinitcpio")
