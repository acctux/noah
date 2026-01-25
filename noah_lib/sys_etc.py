from pathlib import Path
import shutil
import re
import textwrap
from utils import get_logger

log = get_logger("Noah")


def sys_dots(mnt_point: Path, script_dir: Path, sys_dir_cp: list[str]):
    for dir_name in sys_dir_cp:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        log.info("Processing %s -> %s", source_dir, target_dir)
        if not source_dir.exists():
            log.error("Source directory not found: %s", source_dir)
            continue
        shutil.copytree(
            source_dir, target_dir, dirs_exist_ok=True, copy_function=shutil.copy2
        )
        log.info("Copied %s to %s", source_dir, target_dir)


def configure_sudo(user_name: str, mnt_point: Path, pwd_require: bool = True):
    sudoers_file = mnt_point / f"etc/sudoers.d/00_{user_name}"
    if not pwd_require:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) NOPASSWD:ALL"
        prt_val = "without password requirement"
    else:
        sudoers_line = f"{user_name} ALL=(ALL:ALL) ALL"
        prt_val = "with password requirement"
    sudoers_content = textwrap.dedent(f"""\
        {sudoers_line}
        Defaults    insults
        Defaults    passwd_tries=10
        Defaults    lecture=never
        Defaults    passwd_timeout=0
        Defaults    timestamp_timeout=20
        Defaults    timestamp_type=global
        Defaults    editor=/usr/sbin/nvim, !env_editor
    """)
    sudoers_file.write_text(sudoers_content.strip())
    sudoers_file.chmod(0o440)
    log.info(f"Created {sudoers_file} {prt_val} for {user_name}")


def modify_systemd(mnt_point: Path, boot_opts: list[str] = ["quiet", "splash"]) -> None:
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
    loader_file = mnt_point / "boot" / "loader" / "loader.conf"
    loader_file.write_text("default @saved\ntimeout 1\neditor no\n")
    loader_file.chmod(0o644)
    log.info(f"Modified {loader_file}")


def modify_fstab(mnt_point: Path) -> None:
    fstab_path = mnt_point / "etc" / "fstab"
    content = fstab_path.read_text()
    # ^(?!#)       → ignore comments
    # .*?          → match any characters up to the option we want
    # \bfmask=\d+  → word boundary, then 'fmask=' followed by digits
    # \bdmask=\d+  → word boundary, then 'dmask=' followed by digits
    content = re.sub(r"^(?!#).*?\bfmask=\d+", "fmask=0077", content, flags=re.MULTILINE)
    content = re.sub(r"^(?!#).*?\bdmask=\d+", "dmask=0077", content, flags=re.MULTILINE)
    fstab_path.write_text(content)


def modify_mkinit(mnt_point: Path, hooks: list[str]):
    mkinitcpio_conf_path = f"{mnt_point}/etc/mkinitcpio.conf"
    with open(mkinitcpio_conf_path, "r+") as mkinit:
        content = mkinit.read()
        content = re.sub(r"\nHOOKS=.*", f"\nHOOKS=({' '.join(hooks)})", content)
        mkinit.seek(0)
        mkinit.truncate()
        mkinit.write(content)
