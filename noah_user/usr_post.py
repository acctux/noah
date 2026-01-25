import os
from pathlib import Path
from utils import get_logger
import shutil
import subprocess
import pyperclip

log = get_logger("Noah")


def cleanup(HOME: Path):
    for f in [HOME / "keys" / "pass.txt"]:
        if f.exists():
            f.unlink()
    for d in [HOME / "archinstall"]:
        if d.exists():
            shutil.rmtree(d)


def pass_and_input(password_file: str, pass_dir: Path):
    password = (pass_dir / password_file).read_text().strip()
    os.environ["CLIPBOARD_STATE"] = "sensitive"
    pyperclip.copy(password)
    log.info("Password copied to clipboard.")
    cmd = ["firedragon", "https://addons.mozilla.org/en-US/firefox/addon/proton-pass/"]
    subprocess.Popen(cmd).wait()
    pyperclip.copy("")
    log.info("Clipboard cleared.")
    os.environ.pop("CLIPBOARD_STATE", None)


def launch_apps():
    apps = ["firedragon", "protonmail-bridge", "betterbird", "steam"]
    processes = []
    for app in apps:
        processes.append(subprocess.Popen(app))
    for app, process in zip(apps, processes):
        process.wait()
        log.info(f"{app} closed")
