import re
from dataclasses import dataclass
from pathlib import Path
from utils import log, modify_mkinit
from archinstall.lib.installer import Installer


@dataclass
class SnapperProfile:
    name: str
    mount: str
    limit_monthly: int = 0
    number_limit: int = 15
    limit_hourly: int = 5
    limit_daily: int = 5
    limit_weekly: int = 5
    limit_yearly: int = 0

    def to_config_dict(self) -> dict[str, int]:
        return {
            "NUMBER_LIMIT": self.number_limit,
            "TIMELINE_LIMIT_HOURLY": self.limit_hourly,
            "TIMELINE_LIMIT_DAILY": self.limit_daily,
            "TIMELINE_LIMIT_WEEKLY": self.limit_weekly,
            "TIMELINE_LIMIT_MONTHLY": self.limit_monthly,
            "TIMELINE_LIMIT_YEARLY": self.limit_yearly,
        }


def update_existing_config_files(target_root: Path, profile: SnapperProfile) -> None:
    path = target_root / "etc" / "snapper" / "configs" / profile.name
    if not path.exists():
        return
    try:
        updates = profile.to_config_dict()
        keys_pattern = "|".join(map(re.escape, updates.keys()))
        pattern = re.compile(rf"^(\s*)({keys_pattern})=")
        lines = path.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            if match := pattern.match(line):
                leading_whitespace, key = match.groups()
                new_lines.append(f'{leading_whitespace}{key}="{updates[key]}"')
            else:
                new_lines.append(line)
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        log.error(f"Error modifying config file {path}: {e}")


def inst_snapper(
    installation: Installer,
    username: str | None,
    profiles: list[SnapperProfile] | None = [
        SnapperProfile(name="root", mount="/"),
        SnapperProfile(
            name="home", mount="/home", limit_monthly=3, limit_daily=7, number_limit=20
        ),
    ],
) -> None:
    installation.add_additional_packages("limine-snapper-sync")
    if profiles:
        for profile in profiles:
            cmd = f"snapper --no-dbus -c {profile.name} create-config {profile.mount}"
            installation.arch_chroot(cmd)
            if profile.mount == "/home" and username:
                cmd = f"snapper --no-dbus -c {profile.name} set-config 'ALLOW_USERS={username}' SYNC_ACL='yes'"
                installation.arch_chroot(cmd)
            update_existing_config_files(installation.target, profile)
        installation.enable_service(["snapper-cleanup.timer", "snapper-timeline.timer"])
        modify_mkinit(
            installation.target, hook="btrfs-overlayfs", after_hook="filesystems"
        )
