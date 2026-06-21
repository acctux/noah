import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from archinstall.lib.args import ArchConfig
from archinstall.lib.installer import Installer
from archinstall.lib.models import Bootloader
from utils import copy_it, log, write_etc_file


# ==============================================================================
# 0. UTILITY FUNCTIONS
# ==============================================================================
def modify_mkinit(mnt_point: Path, hook: str, after_hook: str) -> None:
    mkinit_conf = mnt_point / "etc" / "mkinitcpio.conf"
    if not mkinit_conf.exists():
        log.warning(f"mkinitcpio configuration not found at {mkinit_conf}")
        return
    lines = mkinit_conf.read_text(encoding="utf-8").splitlines()
    updated_lines = []
    for line in lines:
        if line.strip().startswith("HOOKS="):
            # Extract content inside parentheses
            start = line.find("(") + 1
            end = line.find(")")
            if start > 0 and end > start:
                hooks = line[start:end].split()
                if hook not in hooks and after_hook in hooks:
                    next_index = hooks.index(after_hook) + 1
                    hooks.insert(next_index, hook)
                    line = f"HOOKS=({' '.join(hooks)})"
        updated_lines.append(line)
    mkinit_conf.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


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


@dataclass
class SnapperProfile:
    name: str
    mount: str
    limit_monthly: int = 0
    number_limit: int = 15
    limit_hourly: int = 5
    limit_daily: int = 5
    limit_weekly: int = 5
    limit_yearly: int = 0

    def to_config_dict(self) -> dict[str, int]:
        return {
            "NUMBER_LIMIT": self.number_limit,
            "TIMELINE_LIMIT_HOURLY": self.limit_hourly,
            "TIMELINE_LIMIT_DAILY": self.limit_daily,
            "TIMELINE_LIMIT_WEEKLY": self.limit_weekly,
            "TIMELINE_LIMIT_MONTHLY": self.limit_monthly,
            "TIMELINE_LIMIT_YEARLY": self.limit_yearly,
        }


def update_existing_config_files(target_root: Path, profile: SnapperProfile) -> None:
    path = target_root / "etc" / "snapper" / "configs" / profile.name
    if not path.exists():
        return
    try:
        updates = profile.to_config_dict()
        keys_pattern = "|".join(map(re.escape, updates.keys()))
        pattern = re.compile(rf"^(\s*)({keys_pattern})=")
        lines = path.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            if match := pattern.match(line):
                leading_whitespace, key = match.groups()
                new_lines.append(f'{leading_whitespace}{key}="{updates[key]}"')
            else:
                new_lines.append(line)
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        log.error(f"Error modifying config file {path}: {e}")


def inst_snapper(
    installation: Installer,
    username: str | None,
    profiles: list[SnapperProfile] | None = [
        SnapperProfile(name="root", mount="/"),
        SnapperProfile(
            name="home", mount="/home", limit_monthly=3, limit_daily=7, number_limit=20
        ),
    ],
) -> None:
    installation.add_additional_packages("limine-snapper-sync")
    if profiles:
        for profile in profiles:
            cmd = f"snapper --no-dbus -c {profile.name} create-config {profile.mount}"
            installation.arch_chroot(cmd)
            if profile.mount == "/home" and username:
                cmd = f"snapper --no-dbus -c {profile.name} set-config 'ALLOW_USERS={username}' SYNC_ACL='yes'"
                installation.arch_chroot(cmd)
            update_existing_config_files(installation.target, profile)
        installation.enable_service(["snapper-cleanup.timer", "snapper-timeline.timer"])
        modify_mkinit(
            installation.target, hook="btrfs-overlayfs", after_hook="filesystems"
        )


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
    username = None
    if config.auth_config and config.auth_config.users:
        username = config.auth_config.users[0].username
    inst_snapper(installation, username)
