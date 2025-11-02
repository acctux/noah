import subprocess
import time
from pathlib import Path
import logging

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
PKG_D = ROOT_DIR / "pkg"


# Custom logging level
SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

# Color mapping
COLORS = {
    "INFO": "\033[36m",  # cyan
    "SUCCESS": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "RESET": "\033[0m",
}


# Custom formatter
class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{COLORS['RESET']}"


# Configure logger
log = logging.getLogger("keysync")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
log.addHandler(handler)


# Add success helper
def success(self, message, *args, **kwargs):
    if self.isEnabledFor(25):
        self._log(25, message, args, **kwargs)


setattr(logging.Logger, "success", success)


def resolve_pkgs(pkg_dir: Path, pkg_list: str) -> list[str]:
    """Resolve and load a single .list file into a list of package names."""
    pkglist_path = (pkg_dir / f"{pkg_list}.list").resolve()
    log.info(f"Resolved path: {pkglist_path}")

    if not pkglist_path.is_file():
        raise FileNotFoundError(f"Package list not found: {pkglist_path}")

    pkgs = []
    with pkglist_path.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pkgs.append(line)
    return pkgs


def install_pkg_list(pkg_list: str, pkg_dir: Path):
    """Install a single package list with retries."""
    packages_to_install = resolve_pkgs(pkg_dir, pkg_list)

    if not packages_to_install:
        log.warning("No packages to install.")
        return

    for attempt in range(1, 6):  # up to 5 attempts
        log.info(f"Installing packages (attempt {attempt})...")
        try:
            subprocess.run(
                ["pacman", "-Syu", "--noconfirm", "--needed", *packages_to_install],
                check=True,
            )
            log.info("All packages installed successfully.")
            return
        except subprocess.CalledProcessError:
            log.warning("Package installation failed. Retrying in 5 seconds...")
            time.sleep(5)

    log.error("Failed to install packages after multiple attempts.")
