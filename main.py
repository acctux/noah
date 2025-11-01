from pathlib import Path
from outsidepy.outside import inside_env

import outsidepy.scripts.pacman as pac

SCRIPT_DIR = Path(__file__).resolve()
PKG_D = Path(SCRIPT_DIR / "pkg")
PKG_LISTS = ["business", "chaotic", "cli-tools", "coding", "dependencies"]


def main():
    inside_env()
    pac.install_pkg_list("dependencies", PKG_D)
