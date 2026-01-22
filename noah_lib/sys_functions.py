#################-MAIN FUNCTIONS-#################
import getpass
from pathlib import Path
import shlex
from utils import get_logger
from archinstall.lib.installer import SysCommand

log = get_logger("User")


def run_cc(
    commands: list[str],
    mnt_point: Path,
    user_name: str | None = None,
    peek: bool = True,
) -> None:
    script_path = "var/tmp/user-commands.sh"
    chroot_path = mnt_point / script_path
    chroot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chroot_path, "w") as script:
        script.write("#!/bin/bash\n")
        if peek:
            script.write("set -e\n")
        for cmd in commands:
            script.write(cmd + "\n")
    chroot_path.chmod(0o755)
    cmd = f"bash /{script_path}"
    if user_name:
        cmd = f"su - {user_name} -c {shlex.quote(cmd)}"
    SysCommand(f"arch-chroot -S {mnt_point} {cmd}")
    chroot_path.unlink()


def modify_systemd(
    mnt_point: Path,
    boot_opts: list[str] = ["quiet", "splash"],
) -> None:
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


def type_password(user_name: str) -> str:
    while True:
        pwd1 = getpass.getpass(f"Enter password for {user_name}: ")
        pwd2 = getpass.getpass("Re-enter password: ")
        if not pwd1 or pwd1 != pwd2:
            log.info("Try again.")
            continue
        return pwd1


def ensure_password(usb_key_dir: str, key_files: list[str], user_name: str) -> str:
    key_path = Path("/root") / usb_key_dir / key_files[3]
    if key_path.exists():
        try:
            pw = key_path.read_text().strip()
            log.info(f"Password loaded from '{key_path}'.")
            return pw
        except Exception as e:
            log.error(f"Failed to read password from '{key_path}': {e}")
    log.warning(f"Password file '{key_path}' not found or unreadable.")
    return type_password(user_name)
