from pathlib import Path
import outsidepy.outside as out

import insidepy.scripts.pacman as pac

SCRIPT_DIR = Path(__file__).resolve()
PKG_D = Path(SCRIPT_DIR / "pkg")
PKG_LISTS = ["business", "chaotic", "cli-tools", "coding", "dependencies"]


def main():
    out.outside_env()
    pac.install_pkg_list("dependencies", PKG_D)
