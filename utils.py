import shutil
from pathlib import Path
import sys
import logging
import subprocess


#########################
# LOG
#########################
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[34m",  # blue
        logging.WARNING: "\033[93m",
        logging.ERROR: "\033[31m",
    }
    RESET = "\033[0m"
    NAME = "\033[93m"

    def format(self, record):
        name = f"{self.NAME}{record.name}{self.RESET}"
        msg = f"{self.COLORS.get(record.levelno, '')}{record.getMessage()}{self.RESET}"
        return f"{name}: {msg}"


def get_logger(log_name=None, level=logging.INFO):
    log = logging.getLogger(log_name)
    if log.handlers:
        return log
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter())
    log.addHandler(handler)
    log.setLevel(level)
    log.propagate = False
    return log


log = get_logger("Noah")


def run_dmc(
    cmd: list[str],
    check: bool = False,
    input_text: str = "",
    shell: bool = False,
    cwd=None,
    interactive=False,
):
    if interactive:
        return subprocess.Popen(cmd).wait()
    log = get_logger("Run CMD")
    try:
        log.info(" ".join(cmd))
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
            shell=shell,
            cwd=cwd,
        )
        if result.stdout:
            log.info(f"stdout: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(cmd)} (exit {e.returncode})")
        if e.stdout:
            log.info(f"stdout: {e.stdout.strip()}")
        if e.stderr:
            log.error(f"stderr: {e.stderr.strip()}")
        return e


def yes_no(prompt: str, default: bool = True) -> bool:
    while True:
        r = (
            input(f"\033[92m{prompt} {'(Y/n)' if default else '(y/N)'}: \033[0m")
            .strip()
            .lower()
        )
        if r == "":
            return default
        if r in ("y"):
            return True
        if r in ("n"):
            return False


#########################
# UTILS
#########################
def copy_it(src: Path, dest: Path) -> None:
    if not src.exists():
        log.warning(f"{src} not found")
        return
    if src.is_file():
        dest = dest / src.name if dest.is_dir() else dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        log.info(f"Copied file: {src} -> {dest}")
    elif src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True, ignore_dangling_symlinks=True)
        log.info(f"Copied directory: {src} -> {dest}")


def write_etc_file(mnt_point: Path, files_to_write: dict[str, str]) -> None:
    for filepath, content in files_to_write.items():
        full_path = mnt_point / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if full_path.exists():
            backup_path = full_path.with_suffix(full_path.suffix + ".bak")
            shutil.copy2(full_path, backup_path)
            log.info(f"Backed up {full_path} to {backup_path}")
        with full_path.open("w") as file:
            file.write(content)
        log.info(f"Content written to: {full_path}")


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
