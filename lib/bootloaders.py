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
    """Writes a kernel command line option to limine-entry-tool configuration."""
    output_dir = installation.target / "etc" / "limine-entry-tool.d"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / f"{filename}.conf"
    target_file.write_text(f"KERNEL_CMDLINE[default]+={kernel_params}\n")
    log.info(f"Wrote extra option '{kernel_params}' to {target_file}")
    if run_refresh:
        installation.arch_chroot("limine-mkinitcpio")


def set_default_cmdline(installation: Installer) -> None:
    limine_conf = installation.target / "boot" / "EFI" / "arch-limine" / "limine.conf"
    if not limine_conf.exists():
        log.warning(f"Limine configuration file not found at {limine_conf}")
        cmdline = ""
    for line in limine_conf.read_text().splitlines():
        line = line.strip()
        if line.startswith("cmdline:"):
            cmdline = line.split(":", 1)[1].strip()
            log.info(f"Retrieved cmdline: {cmdline}")
    write_limine_opt(installation, "original_flags", cmdline, run_refresh=True)


def set_boot_default(mountpoint: Path) -> None:
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
    for line in limine_conf.read_text().splitlines():
        if line.strip().startswith("timeout:"):
            new_lines.extend(["timeout: 1", "remember_last_entry: yes"])
            continue
        new_lines.append(line)
        if line.strip() == "### Theme":
            new_lines.extend(theme)
    limine_conf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    log.info(f"Updated config parameters inside {limine_conf}")


def set_etc_default(mnt: Path) -> None:
    default_limine = mnt / "etc" / "default" / "limine"
    copy_it(mnt / "etc" / "limine-entry-tool.conf", default_limine)
    if not default_limine.exists():
        return
    content = default_limine.read_text().splitlines()
    for i, line in enumerate(content):
        if line.strip().startswith("#TARGET_OS_NAME"):
            content[i] = "TARGET_OS_NAME='Arch Linux'"
            break
    default_limine.write_text("\n".join(content) + "\n")


def limine_post(installation: Installer) -> None:
    installation.add_additional_packages("limine-mkinitcpio-hook")
    set_boot_default(installation.target)
    set_etc_default(installation.target)
    set_default_cmdline(installation)


# ==============================================================================
# 2. SUBSYSTEM MODULES
# ==============================================================================
def inst_apparmor(installation: Installer) -> None:
    installation.add_additional_packages(["apparmor", "apparmor.d-git"])
    write_limine_opt(
        installation,
        filename="apparmor",
        kernel_params="lsm=landlock,lockdown,yama,integrity,apparmor,bpf",
        run_refresh=False,
    )
    write_etc_file(
        mnt_point=installation.target,
        files_to_write={
            "etc/apparmor/parser.conf": dedent(
                """\
                write-cache
                cache-loc /etc/apparmor/earlypolicy/
                """
            )
        },
    )
    installation.enable_service("apparmor")


def inst_plymouth(installation: Installer) -> None:
    installation.add_additional_packages("plymouth")
    write_limine_opt(
        installation,
        filename="plymouth",
        kernel_params="quiet splash",
        run_refresh=False,
    )
    modify_mkinit(
        installation.target,
        hook="plymouth",
        after_hook="kms",
    )


# ==============================================================================
# 3. MAIN HANDLING
# ==============================================================================
def bootloader_handling(installation: Installer, config: ArchConfig) -> None:
    boot_conf = config.bootloader_config
    if boot_conf:
        if boot_conf.bootloader == Bootloader.Limine and not boot_conf.uki:
            limine_post(installation)
            inst_apparmor(installation)
            inst_plymouth(installation)
            log.info("Refreshing limine-mkinitcpio hooks cleanly.")
            installation.arch_chroot("limine-mkinitcpio")
