from archinstall.lib.installer import Installer
from utils import copy_file, log
from pathlib import Path


def write_limine_opt(mountpoint: Path, extra_opt: dict[str, str]):
    output_dir = mountpoint / "etc" / "limine-entry-tool.d"
    for filename, opt in extra_opt:
        target_file = output_dir / f"{filename}.conf"
        target_file.write_text(f"KERNEL_CMDLINE[default]+={opt}\n")
        log.info(f"Wrote extra option '{opt}' to {target_file}")


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
    write_limine_opt(installation.target, {"original_flags": cmdline})
    write_limine_conf(installation.target)
    installation.arch_chroot("limine-mkinitcpio")
