import subprocess
import sys
import time
from utils import run_cmd, get_logger, ping

log = get_logger("Noah")


def run_interactive(cmd: list[str], check: bool = True) -> int:
    log.info(f"Running (interactive): {' '.join(cmd)}")
    returncode = subprocess.Popen(
        cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, text=True
    ).wait()
    if check and returncode != 0:
        raise subprocess.CalledProcessError(returncode, cmd)
    return returncode


def run_sudo_commands(
    sudo_cmds=[
        ["sudo", "rm", "/etc/resolv.conf"],
        ["sudo", "resolvconf", "-u"],
        ["sudo", "firewall-cmd", "--set-default-zone=block"],
        ["sudo", "systemctl", "restart", "iwd"],
    ],
):
    def iwctl_scan():
        result = run_cmd(["sudo", "iwctl", "station", "wlan0", "scan"], True)
        if result and result.returncode != 0:
            log.error(f"Failed: {cmd}")
            return
        time.sleep(10)

    for cmd in sudo_cmds:
        result = run_cmd(cmd, True)
        if result and result.returncode != 0:
            log.error(f"Failed: {cmd}")
    time.sleep(1)
    iwctl_scan()
    if not ping:
        iwctl_scan()


def enable_mariadb():
    commands = [
        [
            "sudo",
            "mariadb-install-db",
            "--user=mysql",
            "--basedir=/usr",
            "--datadir=/var/lib/mysql",
        ],
        ["sudo", "systemctl", "start", "mariadb"],
        [
            "sudo",
            "/usr/bin/mariadb",
            "-e",
            (
                "CREATE USER 'user_name'@'localhost' IDENTIFIED BY 'password'; "
                "GRANT ALL PRIVILEGES ON mydb.* TO 'user_name'@'localhost'; "
                "FLUSH PRIVILEGES;"
            ),
        ],
    ]
    for cmd in commands:
        result = run_cmd(cmd, True)
        if result and result.returncode != 0:
            log.error(f"Command failed: {cmd}")
