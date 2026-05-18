from archinstall.lib.args import ArchConfig
import re
from pathlib import Path
from textwrap import dedent

from archinstall.lib.installer import Installer
from archinstall.lib.models import Bootloader
from utils import copy_file, log, write_etc_file


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
    installation: Installer, filename: str, kernel_params: str, run_refresh: bool = True
) -> None:
    """Writes a kernel command line option to limine-entry-tool configuration."""
    output_dir = installation.target / "etc" / "limine-entry-tool.d"
    output_dir.mkdir(parents=True, exist_ok=True)

    target_file = output_dir / f"{filename}.conf"
    target_file.write_text(f"KERNEL_CMDLINE[default]+={kernel_params}\n")
    log.info(f"Wrote extra option '{kernel_params}' to {target_file}")

    if run_refresh:
        installation.arch_chroot("limine-mkinitcpio")


def get_cmdline(mountpoint: Path) -> str:
    """Extracts the default kernel command line configuration from an existing Limine setup."""
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
    """Update timeout and insert 'remember_last_entry' immediately after 'timeout'."""
    limine_conf = mountpoint / "boot" / "limine.conf"
    if not limine_conf.exists():
        return
    lines = limine_conf.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("timeout"):
            lines[i] = "timeout: 1"
            lines.insert(i + 1, "remember_last_entry: yes")
            break
    limine_conf.write_text("\n".join(lines) + "\n")
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
    copy_file(installation.target / "etc" / "limine-entry-tool.conf", default_limine)

    set_target_os(default_limine)
    write_limine_conf(installation.target)

    cmdline = get_cmdline(installation.target)
    # Defer mkinit execution by passing run_refresh=False
    write_limine_opt(
        installation,
        filename="original_flags",
        kernel_params=cmdline,
        run_refresh=False,
    )


###################################
# SYSTEMD-BOOT CONFIGURATION
###################################
def sysd_boot_params(
    mnt_point: Path, plymouth: bool, apparmor: bool, boot_opts: list[str] | None = None
) -> None:
    """Injects mandatory performance, security, and visual options into systemd-boot entry files."""
    opts_to_add = list(boot_opts) if boot_opts else []
    if plymouth:
        opts_to_add.extend(["quiet", "splash"])
    if apparmor:
        opts_to_add.append("lsm=landlock,lockdown,yama,integrity,apparmor,bpf")
    entries_dir = mnt_point / "boot" / "loader" / "entries"
    if not entries_dir.exists():
        return
    for entry in entries_dir.iterdir():
        if not entry.is_file():
            continue
        lines = entry.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("options "):
                existing_opts = line[len("options ") :].split()
                for opt in opts_to_add:
                    if opt not in existing_opts:
                        existing_opts.append(opt)
                lines[i] = "options " + " ".join(existing_opts)
                break
        entry.write_text("\n".join(lines) + "\n")


def modify_fstab(mnt_point: Path) -> None:
    """Enforces secure directory/file masking (0077) on system boot file systems."""
    fstab_path = mnt_point / "etc" / "fstab"
    if not fstab_path.exists():
        return

    content = fstab_path.read_text()
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def install_sysd(mnt_point: Path) -> None:
    """Deploys and initializes systemd-boot loader setups and transaction hooks."""
    sysd_boot_params(mnt_point=mnt_point, plymouth=True, apparmor=True)
    modify_fstab(mnt_point)

    sysd_bootloader_files = {
        "boot/loader/loader.conf": dedent(
            """\
            default @saved
            timeout 1
            editor no
            """
        ),
        "etc/pacman.d/hooks/95-systemd-boot.hook": dedent(
            """\
            [Trigger]
            Type = Package
            Operation = Upgrade
            Target = systemd

            [Action]
            Description = Gracefully upgrading systemd-boot...
            When = PostTransaction
            Exec = /usr/bin/systemctl restart systemd-boot-update.service
            """
        ),
    }
    write_etc_file(mnt_point, sysd_bootloader_files)


###################################
# SUBSYSTEM MODULES
###################################
def inst_apparmor(installation: Installer) -> None:
    """Provisions AppArmor user-space utilities and activates system kernel containment profiles."""
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
    """Deploys and configures plymouth modern graphics boot animation framework."""
    installation.add_additional_packages("plymouth")
    write_limine_opt(
        installation,
        filename="plymouth",
        kernel_params="quiet splash",
        run_refresh=False,
    )
    modify_mkinit(installation.target, hook="plymouth", after_hook="kms")


def default_numlock(installation: Installer, sysd: bool) -> None:
    """Configures explicit NumLock activation state variables across early user-space initialization."""
    installation.add_additional_packages("mkinitcpio-numlock")
    if sysd:
        modify_mkinit(
            mnt_point=installation.target, hook="sd-numlock", after_hook="sd-vconsole"
        )
    else:
        modify_mkinit(
            mnt_point=installation.target, hook="numlock", after_hook="consolefont"
        )


def inst_snapper(
    installation: Installer,
    username: str | None,
    snapper_subvolumes: dict[str, str] = {
        "root": "/",
        "home": "/home",
    },
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


###################################
# MAIN HANDLING DISPATCHER
###################################
def bootloader_handling(installation: Installer, config: ArchConfig) -> None:
    """Orchestrates configuration logic maps based on chosen destination boot utilities."""
    if boot_conf := config.bootloader_config:
        if boot_conf.bootloader == Bootloader.Systemd:
            if not boot_conf.uki:
                install_sysd(installation.target)
                default_numlock(installation, sysd=True)

        elif boot_conf.bootloader == Bootloader.Limine:
            if not boot_conf.uki:
                default_numlock(installation, sysd=False)
                install_limine(installation)
                inst_apparmor(installation)
                inst_plymouth(installation)
                log.info("Refreshing limine-mkinitcpio hooks cleanly.")
                installation.arch_chroot("limine-mkinitcpio")

    if auth_conf := config.auth_config:
        username = auth_conf.users[0].username
    inst_snapper(installation, username)
