import subprocess
import time
from pathlib import Path
from pyutils.my_log import log

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
PKG_D = ROOT_DIR / "pkg"


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


log.info(f"{PKG_D}")
install_pkg_list("dependencies", PKG_D)
