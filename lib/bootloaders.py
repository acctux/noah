from archinstall.lib.models.bootloader import BootloaderConfiguration
from archinstall.lib.models import Bootloader
from textwrap import dedent
from archinstall.lib.installer import Installer
from utils import copy_file, log, write_etc_file, modify_mkinit
from pathlib import Path
import re


###################################
# LIMINE
###################################
def write_limine_opt(installation: Installer, filename: str, kernel_params: str):
    output_dir = installation.target / "etc" / "limine-entry-tool.d"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / f"{filename}.conf"
    target_file.write_text(f"KERNEL_CMDLINE[default]+={kernel_params}\n")
    log.info(f"Wrote extra option '{kernel_params}' to {target_file}")
    installation.arch_chroot("limine-mkinitcpio")


def get_cmdline(
    mountpoint: Path,
) -> str:
    limine_conf = mountpoint / "boot" / "EFI" / "arch-limine" / "limine.conf"
    cmdline = ""
    with limine_conf.open() as f:
        for line in f:
            line = line.strip()
            if line.startswith("cmdline:"):
                cmdline = line.split(":", 1)[1].strip()
                log.info(cmdline)
                break
    return cmdline


def write_limine_conf(mountpoint: Path):
    limine_conf = mountpoint / "boot" / "limine.conf"
    lines = limine_conf.read_text().splitlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith("timeout"):
            new_lines.append("timeout: 1")
            new_lines.extend(["remember_last_entry: yes"])
        else:
            new_lines.append(line)
    limine_conf.write_text("\n".join(new_lines) + "\n")
    log.info(f"Updated {limine_conf}")


def set_target_os(default_limine: Path):
    with open(default_limine) as default:
        content = default.read().splitlines()
    for i, line in enumerate(content):
        stripped = line.strip()
        if stripped.startswith("#TARGET_OS_NAME"):
            content[i] = "TARGET_OS_NAME='Arch Linux"
    with open(default_limine, "w") as default:
        default.write("\n".join(content) + "\n")


def install_limine(installation: Installer):
    installation.add_additional_packages("limine-mkinitcpio-hook")
    default_limine = installation.target / "etc" / "default" / "limine"
    copy_file(installation.target / "etc" / "limine-entry-tool.conf", default_limine)
    set_target_os(default_limine)
    cmdline = get_cmdline(installation.target)
    write_limine_conf(installation.target)
    write_limine_opt(installation, filename="original_flags", kernel_params=cmdline)


###################################
# SYSTEM D
###################################
def sysd_boot_params(
    mnt_point: Path, plymouth: bool, apparmor: bool, boot_opts=[]
) -> None:
    if plymouth:
        boot_opts.extend(["quiet", "splash"])
    if apparmor:
        boot_opts.append("lsm=landlock,lockdown,yama,integrity,apparmor,bpf")
    entries_dir = mnt_point / "boot" / "loader" / "entries"
    for entry in entries_dir.iterdir():
        lines = entry.read_text().splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("options "):
                existing_opts = line[len("options ") :].split()
                for opt in boot_opts:
                    if opt not in existing_opts:
                        existing_opts.append(opt)
                line = "options " + " ".join(existing_opts)
            new_lines.append(line)
        entry.write_text("\n".join(new_lines) + "\n")


def modify_fstab(mnt_point: Path) -> None:
    fstab_path = mnt_point / "etc" / "fstab"
    content = fstab_path.read_text()
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def install_sysd(mnt_point: Path):
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


def inst_apparmor(installation: Installer):
    installation.add_additional_packages(["apparmor", "apparmor.d-git"])
    write_limine_opt(
        installation, "apparmor", "lsm=landlock,lockdown,yama,integrity,apparmor,bpf"
    )
    content = {
        "etc/apparmor/parser.conf": dedent(
            """\
            write-cache
            cache-loc /etc/apparmor/earlypolicy/
            Optimize=compress-fast
            """
        )
    }
    write_etc_file(installation.target, content)
    installation.enable_service("apparmor")


def inst_plymouth(installation: Installer):
    installation.add_additional_packages("plymouth")
    write_limine_opt(installation, filename="plymouth", kernel_params="quiet splash")
    modify_mkinit(installation.target, hook="plymouth", after="kms")


def default_numlock(installation: Installer, sysd: bool):
    installation.add_additional_packages("mkinitcpio-numlock")
    if sysd:
        modify_mkinit(installation.target, "sd-numlock", "sd-vconsole")
    else:
        modify_mkinit(installation.target, "numlock", "consolefont")


def bootloader_handling(installation: Installer, boot_config: BootloaderConfiguration):
    if boot_config.bootloader == Bootloader.Systemd:
        if not boot_config.uki:
            sysd_boot_params(installation.target, plymouth=True, apparmor=True)
            default_numlock(installation, sysd=True)
    elif boot_config.bootloader == Bootloader.Limine:
        default_numlock(installation, sysd=False)
        modify_mkinit(installation.target, "numlock", "consolefont")
        install_limine(installation)
        inst_apparmor(installation)
        inst_plymouth(installation)
