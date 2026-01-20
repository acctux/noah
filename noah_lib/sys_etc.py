from pathlib import Path
import shutil
import textwrap
from noah_lib.utils import get_logger

log = get_logger("Noah")


def sys_dots(
    mnt_point: Path,
    script_dir: Path,
    sys_dir_cp: list[str],
):
    for dir_name in sys_dir_cp:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        log.info("Processing %s -> %s", source_dir, target_dir)
        if not source_dir.exists():
            log.error("Source directory not found: %s", source_dir)
            continue
        try:
            shutil.copytree(
                source_dir,
                target_dir,
                dirs_exist_ok=True,
                copy_function=shutil.copy2,
            )
            log.info("Copied %s to %s", source_dir, target_dir)
        except Exception:
            log.exception("Failed copying %s to %s", source_dir, target_dir)


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


def modify_fstab(mnt_point: Path) -> None:
    fstab = mnt_point / "etc" / "fstab"
    out = []
    for line in fstab.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            out.append(line)
            continue
        parts = line.split()
        if len(parts) < 6:
            out.append(line)
            continue
        opts = parts[3].split(",")
        for i, opt in enumerate(opts):
            if opt.startswith("fmask="):
                opts[i] = "fmask=0077"
            elif opt.startswith("dmask="):
                opts[i] = "dmask=0077"
        parts[3] = ",".join(opts)
        out.append("\t".join(parts))
    fstab.write_text("\n".join(out) + "\n")
