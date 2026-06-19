from archinstall.lib.args import ArchConfig
from pathlib import Path
from textwrap import dedent
from archinstall.lib.installer import Installer
from archinstall.lib.models import Bootloader
from utils import copy_it, log, write_etc_file


# ==============================================================================
# 0. UTILITY FUNCTIONS
# ==============================================================================
def modify_mkinit(mnt_point: Path, hook: str, after_hook: str) -> None:
    mkinit_conf = f"/{mnt_point}/etc/mkinitcpio.conf"
    with open(mkinit_conf, "r") as mkinit:
        content = mkinit.read().splitlines()
    for i, line in enumerate(content):
        if line.startswith("HOOKS="):
            start = line.find("(") + 1
            end = line.find(")")
            inside_parens = line[start:end]
            hooks = inside_parens.split()
            if hook not in hooks:
                next_index = hooks.index(after_hook) + 1
                hooks.insert(next_index, hook)
            content[i] = f"HOOKS=({' '.join(hooks)})"
    with open(mkinit_conf, "w") as mkinit:
        mkinit.write("\n".join(content) + "\n")


###################################
# LIMINE CONFIGURATION
###################################
def write_limine_opt(
    installation: Installer,
    filename: str,
    kernel_params: str,
    run_refresh: bool = True,
) -> None:
    output_dir = installation.target / "etc" / "limine-entry-tool.d"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / f"{filename}.conf"
    target_file.write_text(f"KERNEL_CMDLINE[default]+={kernel_params}\n")
    log.info(f"Wrote extra option '{kernel_params}' to {target_file}")
    if run_refresh:
        installation.arch_chroot("limine-mkinitcpio")


def get_cmdline(mountpoint: Path) -> str:
    limine_conf = mountpoint / "boot" / "EFI" / "arch-limine" / "limine.conf"
    if not limine_conf.exists():
        log.warning(f"Limine configuration file not found at {limine_conf}")
        return ""
    with limine_conf.open() as f:
        for line in f:
            line = line.strip()
            if line.startswith("cmdline:"):
                cmdline = line.split(":", 1)[1].strip()
                log.info(f"Retrieved cmdline: {cmdline}")
                return cmdline
    return ""


def write_limine_conf(mountpoint: Path) -> None:
    limine_conf = mountpoint / "boot" / "limine.conf"
    if not limine_conf.exists():
        return
    branding_block = [
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
    for line in limine_conf.read_text().splitlines():
        # Match and update timeout parameters
        if line.strip().startswith("timeout:"):
            new_lines.append("timeout: 1")
            new_lines.append("remember_last_entry: yes")
            continue  # Skip appending the original 'timeout' line
        new_lines.append(line)
        if line.strip() == "### Theme":
            new_lines.extend(branding_block)
    limine_conf.write_text("\n".join(new_lines) + "\n")
    log.info(f"Updated config parameters inside {limine_conf}")


def set_target_os(default_limine: Path) -> None:
    """Sets the target OS string within the global Limine defaults file."""
    if not default_limine.exists():
        return
    content = default_limine.read_text().splitlines()
    for i, line in enumerate(content):
        if line.strip().startswith("#TARGET_OS_NAME"):
            content[i] = "TARGET_OS_NAME='Arch Linux'"
            break
    default_limine.write_text("\n".join(content) + "\n")


def install_limine(installation: Installer) -> None:
    """Performs global installation of the Limine bootloader environment."""
    installation.add_additional_packages("limine-mkinitcpio-hook")
    default_limine = installation.target / "etc" / "default" / "limine"
    copy_it(installation.target / "etc" / "limine-entry-tool.conf", default_limine)
    set_target_os(default_limine)
    write_limine_conf(installation.target)
    cmdline = get_cmdline(installation.target)
    write_limine_opt(installation, "original_flags", cmdline, False)


###################################
# SUBSYSTEM MODULES
###################################
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
            cache-loc /var/cache/apparmor/
            """
        )
    }
    write_etc_file(installation.target, content)
    installation.enable_service("apparmor")


def inst_plymouth(installation: Installer) -> None:
    installation.add_additional_packages("plymouth")
    write_limine_opt(installation, "plymouth", "quiet splash", False)
    modify_mkinit(installation.target, hook="plymouth", after_hook="kms")


def inst_snapper(
    installation: Installer,
    username: str | None,
    snapper_subvolumes: dict[str, str] = {"root": "/", "home": "/home"},
):
    installation.add_additional_packages("limine-snapper-sync")
    write_etc_file(
        installation.target,
        {
            "etc/systemd/system/snapper-timeline.timer.d/15-timeline.conf": dedent(
                """\
                [Timer]
                OnCalendar=
                OnCalendar=*:0/15
                """
            ),
            "etc/systemd/system/snapper-cleanup.timer.d/20-cleanup.conf": dedent(
                """\
                [Timer]
                OnUnitActiveSec=1h
                """
            ),
        },
    )
    for config_name, mountpoint in snapper_subvolumes.items():
        installation.arch_chroot(
            f"snapper --no-dbus -c {config_name} create-config {mountpoint}"
        )
    if username:
        installation.arch_chroot(
            f"snapper --no-dbus -c {config_name} set-config 'ALLOW_USERS={username}' SYNC_ACL='yes'"
        )
    installation.enable_service(["snapper-cleanup.timer", "snapper-timeline.timer"])
    modify_mkinit(installation.target, hook="btrfs-overlayfs", after_hook="filesystems")


def default_numlock(installation: Installer) -> None:
    installation.add_additional_packages("mkinitcpio-numlock")
    modify_mkinit(installation.target, "numlock", after_hook="consolefont")


###################################
# MAIN HANDLING
###################################
def bootloader_handling(installation: Installer, config: ArchConfig) -> None:
    if boot_conf := config.bootloader_config:
        if boot_conf.bootloader == Bootloader.Limine:
            if not boot_conf.uki:
                install_limine(installation)
                inst_apparmor(installation)
                inst_plymouth(installation)
                default_numlock(installation)
                log.info("Refreshing limine-mkinitcpio hooks cleanly.")
                installation.arch_chroot("limine-mkinitcpio")
    if auth_conf := config.auth_config:
        username = auth_conf.users[0].username
    inst_snapper(installation, username)
