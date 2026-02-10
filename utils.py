from typing import Any, Callable
import json
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
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[41m",
    }
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"

    def format(self, record):
        # Hide levelname for INFO
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


#########################
###########################################################
# CLASSES
###########################################################
class UserSrv(BaseModel):
    target: str
    services: list[str]
    source: Path = Path("/usr/lib/systemd/user")


class UserGitRepo(BaseModel):
    target_dir: str
    repos: list[str]


class NoahConfig:
    def __init__(self, file_path: str):
        self._file_path = Path(file_path)
        self._config: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        if not self._file_path.exists():
            log.error(f"Config file not found: {self._file_path}")
        try:
            self._config = json.loads(self._file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON in {self._file_path}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        value: Any = self._config
        for key in key_path.split("."):
            try:
                value = value[key] if isinstance(value, dict) else value[int(key)]
            except (KeyError, IndexError, ValueError, TypeError):
                return default
        return value

    def _objects(self, key: str, factory: Callable[[dict], Any]) -> list[Any]:
        return [factory(item) for item in self.get(key, [])]

    def user_services(self) -> list[UserSrv]:
        return self._objects(
            "services.user",
            lambda s: UserSrv(
                target=s["target"], services=s["services"], source=Path(s["source_dir"])
            ),
        )

    def git_repos(self) -> list[UserGitRepo]:
        return self._objects(
            "git.repos",
            lambda r: UserGitRepo(target_dir=r["target_dir"], repos=r["repos"]),
        )


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
