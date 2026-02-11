import shutil
from pydantic import BaseModel
import logging
from pathlib import Path
import subprocess
from getpass import getpass
import sys


#########################
# LOG
#########################
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[34m",
        logging.WARNING: "\033[93m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[41m",
    }
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"

    def format(self, record):
        message = f"{record.name}: {record.getMessage()}"
        color = self.COLORS.get(record.levelno, "")
        if color:
            message = f"{color}{message}{self.RESET}"
        if record.levelno == logging.CRITICAL:
            message = f"{self.UNDERLINE}{message}{self.RESET}"
        return message


def get_logger(log_name: str | None = None, level=logging.INFO):
    logger = logging.getLogger(log_name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


log = get_logger("Noah")


###########################################################
# CLASSES
###########################################################
class UserSrv(BaseModel):
    source: str = "/usr/lib/systemd/user"
    services: list[str]
    target: str


class UserGitRepo(BaseModel):
    target_dir: str
    repos: list[str]


#########################
# SRC PASSWORD
#########################
def src_pass_file(usb_key_dir: str, pass_file: str):
    key_path = Path("/root") / usb_key_dir / pass_file
    if key_path.exists():
        try:
            pw = key_path.read_text().strip()
            log.info(f"{key_path} loaded ")
            return pw
        except Exception as e:
            log.error(f"{e}")
    log.warning(f"{key_path} not found or unreadable.")


def copy_file(file: Path, dest: Path) -> None:
    if not file.is_file():
        log.error(f"{file} does not exist")
        return
    if dest.is_dir():
        dest = dest / file.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, dest)
    log.info(f"Copied {file} to {dest}")


def copy_dir(dir: Path, dest: Path) -> None:
    src = Path("/root") / dir
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore_dangling_symlinks=True)


def ind_key_permission(path: Path, f_mode=0o600, d_mode=0o700):
    if path.is_file():
        path.chmod(f_mode)
    path.chmod(d_mode)


#########################
# ASK PASSWORD
#########################
def ask_pass(prompt="Password: ", confirm=True, min_len=6, retries=3) -> str:
    for _ in range(retries):
        pwd = getpass(prompt)
        if len(pwd) < min_len:
            print(f"Password must be at least {min_len} characters.")
            continue
        if confirm and pwd != getpass("Confirm password: "):
            print("Passwords do not match.")
            continue
        return pwd
    raise ValueError("Too many failed attempts.")


def run_cmd(
    cmd: list[str], check: bool = False, input_text: str = "", shell: bool = False
):
    log = get_logger("Run CMD")
    try:
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
            shell=shell,
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


def ping(host: str) -> bool:
    return (
        subprocess.run(
            ["ping", "-c", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
