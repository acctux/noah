from packages.aur import aur_pkgs
import shutil
import json
import re
from lib.datahandler import UserService, NoahConfig
from archinstall.lib.models import Bootloader, User
from pathlib import Path
from archinstall.default_profiles.profile import GreeterType
from archinstall.lib.models.application import PowerManagement, Firewall
from archinstall.lib.args import ArchConfig
from archinstall.lib.installer import Installer
from archinstall.lib.hardware import SysInfo, GfxDriver
from archinstall.lib.profile.profiles_handler import profile_handler
from textwrap import dedent
from utils import write_etc_file, log, copy_it, modify_mkinit
from dataclasses import dataclass


def install_nvidia(installation: Installer):
    packages = [
        "libva-nvidia-driver",
        "nvidia-open",
        "nvidia-prime",
    ]
    installation.add_additional_packages(packages=packages)
    nvidia_files: dict[str, str] = {
        "etc/modprobe.d/nvidia.conf": dedent(
            """\
            options nvidia NVreg_UsePageAttributeTable=1
            options nvidia NVreg_DynamicPowerManagement=0x02
            """
        ),
        "etc/udev/rules.d/99-gpu-symlinks.rules": dedent(
            """\
            # NVIDIA GPU (01:00.0)
            KERNEL=="card*", KERNELS=="*:01:00.0", SUBSYSTEM=="drm", SUBSYSTEMS=="pci", SYMLINK+="dri/nvidia-dgpu"
            KERNEL=="renderD*", KERNELS=="*:01:00.0", SUBSYSTEM=="drm", SUBSYSTEMS=="pci", SYMLINK+="dri/nvidia-dgpu-render"
            # AMD GPU (64:00.0)
            KERNEL=="card*", KERNELS=="*:64:00.0", SUBSYSTEM=="drm", SUBSYSTEMS=="pci", SYMLINK+="dri/amd-igpu"
            KERNEL=="renderD*", KERNELS=="*:64:00.0", SUBSYSTEM=="drm", SUBSYSTEMS=="pci", SYMLINK+="dri/amd-igpu-render"
            """
        ),
    }
    write_etc_file(installation.target, nvidia_files)
    installation.enable_service("nvidia-persistenced")


def replace_ly_config(mnt_point: Path) -> None:
    replacements = {
        "animation": "matrix",
        "bg": "0x00101013",
        "border_fg": "0x00D3DAE3",
        "cmatrix_fg": "0x000000FF",
        "colormix_col1": "0x0000FF00",
        "colormix_col2": "0x000000CC",
        "fg": "0x00D3DAE3",
        "numlock": "true",
        "session_log": ".cache/ly",
    }
    conf = Path(mnt_point / "etc/ly/config.ini")
    lines = conf.read_text().splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        for key, value in replacements.items():
            if stripped.startswith(f"{key}"):
                lines[i] = f"{key} = {value}"
                break
    conf.write_text("\n".join(lines) + "\n")


def ufw_post(installation: Installer, ports_to_open: list[str]):
    for allow_port in ports_to_open:
        installation.arch_chroot(f"ufw allow {allow_port}")


def tuned_post(installation: Installer):
    write_etc_file(
        mnt_point=installation.target,
        files_to_write={
            "etc/tuned/ppd.conf": dedent(
                """\
                [main]
                # The default PPD profile
                default=power-saver
                battery_detection=true
                sysfs_acpi_monitor=true

                [profiles]
                # PPD = TuneD
                power-saver=laptop-battery-powersave
                balanced=laptop-ac-powersave
                performance=balanced

                [battery]
                # PPD = TuneD
                balanced=balanced-battery
                """
            ),
        },
    )


def install_logid(installation: Installer, script_d: Path):
    def k(keys):
        return f'type: "Keypress"; keys: [{", ".join(f'"{key}"' for key in keys)}];'

    def g(direction, keys):
        return (
            f'{{direction: "{direction}"; mode: "OnRelease"; action: {{{k(keys)}}};}}'
        )

    def button(cid, action):
        return f"{{cid: {hex(cid)}; action: {{{action}}};}}"

    def gest(actions_list):
        return f'type: "Gestures"; gestures: ({",".join(actions_list)});'

    buttons = [
        # Forward button
        button(0x56, k(["KEY_LEFTMETA"])),
        # Back button
        button(
            0x53,
            gest(
                [
                    g("None", ["KEY_C"]),
                    g("Right", ["KEY_G"]),
                    g("Left", ["KEY_D"]),
                    g("Up", ["KEY_F"]),
                    g("Down", ["KEY_ESC"]),
                ]
            ),
        ),
        # Gesture button
        button(0xC3, k(["KEY_LEFTMETA", "KEY_LEFTSHIFT"])),
        # Top button
        button(
            0xC4,
            gest(
                [
                    g("None", ["KEY_R"]),
                    g("Right", ["KEY_T"]),
                    g("Left", ["KEY_E"]),
                    g("Up", ["KEY_SPACE"]),
                    g("Down", ["KEY_B"]),
                ]
            ),
        ),
    ]
    installation.add_additional_packages("logiops")
    src_d = script_d / "files" / "logid"
    copy_it(src_d / "loggy.service", installation.target / "etc" / "systemd" / "system")
    copy_it(src_d / "loggy.py", installation.target / "usr" / "local" / "bin")
    write_etc_file(
        mnt_point=installation.target,
        files_to_write={
            "etc/logid.cfg": dedent(
                f"""\
                devices: ({{
                    name: "MX Master 3S";
                    smartshift: {{on: true; threshold: 15;}};
                    hiresscroll: {{hires: true; invert: false; target: false;}};
                    dpi: 6000;
                    buttons: ({",".join(buttons)});
                }});
                """
            ),
        },
    )
    installation.enable_service("loggy")


def install_icons(installation: Installer):
    git = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
    installation.arch_chroot(f"git clone {git}")
    installation.arch_chroot("bash ./WhiteSur-icon-theme/install.sh")
    installation.arch_chroot("rm -rf ./WhiteSur-icon-theme")
    icon_path = installation.target / "usr/share/icons"
    white_sur_light = icon_path / "WhiteSur-light"
    if white_sur_light.exists():
        shutil.rmtree(white_sur_light)
        log.info(f"Removed {white_sur_light}")
    themes_to_modify = []
    for folder in icon_path.iterdir():
        if folder.is_dir() and ("-dark" in folder.name or "WhiteSur" in folder.name):
            themes_to_modify.append(folder)
    for theme_dir in themes_to_modify:
        for svg_file in theme_dir.rglob("*.svg"):
            if svg_file.is_file():
                text = svg_file.read_text()
                if "#ffffff" in text:
                    svg_file.write_text(text.replace("#ffffff", "#F4F5F6"))
                    log.info(f"Modified {svg_file}")


def set_extensions(
    mnt_point: Path,
    browser: str,
    extension_ids: list[str] = [
        "return-youtube-dislikes",
        "leechblock-ng",
        "proton-pass",
        "firefox-color",
        "darkreader",
        "flagfox",
        "ublock-origin",
    ],
) -> None:
    """Set Firefox extensions from a list of extension IDs."""
    new_install = [
        f"https://addons.mozilla.org/firefox/downloads/latest/{ext}/latest.xpi"
        for ext in extension_ids
    ]
    file_path = mnt_point / "usr" / "lib" / browser / "distribution" / "policies.json"
    data = {}
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text())
        except json.JSONDecodeError:
            log.warning(f"Corrupt JSON in {file_path}, resetting.")
    policies = data.setdefault("policies", {})
    extensions = policies.setdefault("Extensions", {})
    extensions["Install"] = new_install
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2))
    log.info(f"'Extensions.Install' for {browser} has been overwritten.")


def sys_file_copy(mnt_point: Path, script_dir: Path, dirs_to_cp=["etc", "usr"]) -> None:
    for dir_name in dirs_to_cp:
        source_dir = script_dir / dir_name
        target_dir = mnt_point / dir_name
        copy_it(source_dir, target_dir)


def kde_fuse_and_nss(mnt_point: Path) -> None:
    def update_config(file_path: Path, match: str, new_line: str) -> None:
        lines = file_path.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.lstrip().startswith(match):
                lines[i] = new_line
                break
        file_path.write_text("\n".join(lines) + "\n")

    update_config(mnt_point / "etc/fuse.conf", "#user_allow_other", "user_allow_other")
    update_config(
        mnt_point / "etc/nsswitch.conf",
        "hosts:",
        "hosts: mymachines mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return] files myhostname dns",
    )


def inst_systemd_oomd(installation: Installer):
    write_etc_file(
        mnt_point=installation.target,
        files_to_write={
            "usr/lib/systemd/oomd.conf.d/10-oomd-defaults.conf": dedent(
                """\
                [OOM]
                DefaultMemoryPressureDurationSec=20s
                """
            ),
            "usr/lib/systemd/system/system.slice.d/10-oomd-per-slice-defaults.conf": dedent(
                """\
                [Slice]
                ManagedOOMMemoryPressure=kill
                ManagedOOMMemoryPressureLimit=80%
                """
            ),
            "usr/lib/systemd/user/slice.d/10-oomd-per-slice-defaults.conf": dedent(
                """\
                [Slice]
                ManagedOOMMemoryPressure=kill
                ManagedOOMMemoryPressureLimit=80%
                """
            ),
        },
    )
    installation.enable_service("systemd-oomd")


def install_powertop(installation: Installer):
    installation.add_additional_packages("powertop")
    srv_name = "powertop"
    write_etc_file(
        installation.target,
        {
            f"etc/systemd/system/{srv_name}.service": dedent(
                """\
                [Unit]
                Description=Powertop tunings

                [Service]
                Type=oneshot
                RemainAfterExit=yes
                ExecStart=/usr/bin/powertop --auto-tune

                [Install]
                WantedBy=multi-user.target sleep.target
                """
            ),
        },
    )
    installation.enable_service("powertop")


def inst_pac_contrib():
    pass


network_files: dict[str, str] = {
    "etc/iwd/main.conf": dedent(
        """\
        [Network]
        NameResolvingService=resolvconf
        """
    ),
    "etc/systemd/system/iwd.service.d/override.conf": dedent(
        """\
        [Service]
        ReadWritePaths=/etc/resolv.conf
        """
    ),
    "etc/systemd/network/20-usb-tether.network": dedent(
        """\
        [Match]
        Name=enp*

        [Network]
        DHCP=yes

        [DHCPv4]
        RouteMetric=100
        """
    ),
    "etc/resolvconf.conf": dedent(
        """\
        resolv_conf=/etc/resolv.conf
        name_servers="::1 127.0.0.1"
        """
    ),
    "etc/NetworkManager/conf.d/rc-manager.conf": dedent(
        """\
        [main]
        rc-manager=resolvconf
        """
    ),
    "etc/chrony.conf": dedent(
        """\
        server 0.arch.pool.ntp.org iburst
        server 1.arch.pool.ntp.org iburst
        server 2.arch.pool.ntp.org iburst
        server 3.arch.pool.ntp.org iburst
        driftfile /var/lib/chrony/drift
        rtcsync
        makestep 1.0 3
        leapseclist /usr/share/zoneinfo/leap-seconds.list
        logdir /var/log/chrony
        log measurements statistics tracking
        allow 127.0.0.1
        """
    ),
    "etc/named.conf": dedent(
        """\
        tls cloudflare {
            remote-hostname "one.one.one.one";
        };
        options {
            directory "/var/named";
            listen-on { 127.0.0.1; };
            listen-on-v6 { ::1; };
            allow-recursion {
                127.0.0.1;
                ::1;
            };
            forward only;
            forwarders port 853 tls cloudflare {
                1.1.1.1;
                1.0.0.1;
                2606:4700:4700::1111;
                2606:4700:4700::1001;
            };
        };
        """
    ),
}
etc_files_to_write: dict[str, str] = {
    "etc/sysctl.d/99-sysctl.conf": dedent(
        """\
        vm.max_map_count = 2147483642
        # Disable NMI watchdog
        kernel.nmi_watchdog = 0
        # To hide any kernel messages from the console
        kernel.printk = 3 3 3 3
        # Restricting access to kernel pointers in the proc filesystem
        kernel.kptr_restrict = 2
        # May help prevent losing packets
        net.core.netdev_max_backlog = 4096
        """
    ),
    "etc/conf.d/pacman-contrib": 'PACCACHE_ARGS="-k 2"\n',
    "etc/systemd/journald.conf.d/00-journal-size.conf": dedent(
        """\
        [Journal]
        SystemMaxUse=50M
        """
    ),
    "etc/modprobe.d/blacklist.conf": dedent(
        """\
        # Blacklist the Intel TCO Watchdog/Timer module
        blacklist iTCO_wdt
        # Blacklist the AMD SP5100 TCO Watchdog/Timer module (Required for Ryzen cpus)
        blacklist sp5100_tco"
        """
    ),
    "etc/udisks2/mount_options.conf": dedent(
        """\
        [defaults]
        # 'ntfs' signature, the new 'ntfs3' kernel driver
        ntfs:ntfs3_defaults=uid=$UID,gid=$GID
        ntfs:ntfs3_allow=uid=$UID,gid=$GID,umask,dmask,fmask,iocharset,discard,nodiscard,sparse,nosparse,hidden,nohidden,sys_immutable,showmeta,noshowmeta,prealloc,noprealloc,hide_dot_files,nohide_dot_files,windows_names,nocase,case
        """
    ),
    "etc/udev/rules.d/99-thunderbolt.rules": dedent(
        """\
        ACTION=="add", SUBSYSTEM=="thunderbolt", ATTR{authorized}=="0", ATTR{authorized}="1"
        """
    ),
}


@dataclass
class SnapperProfile:
    name: str
    mount: str
    number_limit: int
    limit_monthly: int
    limit_hourly: int
    limit_daily: int
    limit_weekly: int
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


def update_existing_snapper_files(target_root: Path, profile: SnapperProfile) -> None:
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


def snapper_post(
    installation: Installer,
    users: list[User] | None,
    profiles: list[SnapperProfile] = [
        SnapperProfile(
            name="root",
            mount="/",
            number_limit=15,
            limit_hourly=5,
            limit_daily=5,
            limit_weekly=5,
            limit_monthly=0,
        ),
        SnapperProfile(
            name="home",
            mount="/home",
            number_limit=20,
            limit_hourly=5,
            limit_daily=7,
            limit_weekly=5,
            limit_monthly=3,
        ),
    ],
) -> None:
    installation.add_additional_packages("limine-snapper-sync")
    modify_mkinit(installation.target, hook="btrfs-overlayfs", after_hook="filesystems")
    if profiles:
        for profile in profiles:
            if users and profile.mount == "/home":
                for user in users:
                    cmd = f"snapper --no-dbus -c {profile.name} set-config 'ALLOW_USERS={user.username}' SYNC_ACL='yes'"
                    installation.arch_chroot(cmd)
            update_existing_snapper_files(installation.target, profile)


###################################
# USR_SVC
###################################
def hide_apps(installation: Installer, user: str, apps_to_hide: list[str]):
    for app in apps_to_hide:
        file_p = f"home/{user}/.local/share/applications/{app}.desktop"
        (installation.target / file_p).write_text("[Desktop Entry]\nNoDisplay=true\n")
        installation.chown(user, f"/{file_p}")


def create_automount(installation: Installer, users: list[User]):
    etc_file = {
        "etc/polkit-1/rules.d/49-rules.rules": dedent(
            """\
            polkit.addRule(function(action, subject) {
                if (
                    subject.isInGroup("storage") &&
                    (
                        action.id == "org.freedesktop.udisks2.filesystem-mount" ||
                        action.id == "org.freedesktop.udisks2.filesystem-mount-system" ||
                        action.id == "org.freedesktop.udisks2.encrypted-unlock" ||
                        action.id == "org.freedesktop.udisks2.encrypted-unlock-system"
                    )
                ) {
                    return polkit.Result.YES;
                }
                if (
                    action.id === "org.kde.kpmcore.externalcommand.init" &&
                    subject.isInGroup("wheel")
                ) {
                    return polkit.Result.YES;
                }
            });
            """
        )
    }
    write_etc_file(installation.target, etc_file)
    for user in users:
        installation.arch_chroot(f"usermod -aG storage {user.username}")


def enable_user_serv(installation: Installer, unit: UserService, username: str) -> None:
    sources = unit.get_source_paths(username)
    targets = unit.get_target_paths(username)
    for src, tgt in zip(sources, targets):
        installation.arch_chroot(f"mkdir -p {tgt.parent}", username)
        installation.arch_chroot(f"ln -sfn {src} {tgt}", username)
        log.info("Enabled service: %s -> %s", src, tgt)


def user_service(
    installation: Installer,
    user: str,
    terminal: str,
    current_script_dir: Path,
    user_script="user_setup.py",
) -> None:
    if terminal.strip().lower() == "kitty":
        terminal = "kitty --hold"
    if terminal.strip().lower() == "alacritty":
        terminal = "alacritty -e"
    user_script_dir = f"home/{user}/{current_script_dir.name}"
    run_script = f"/{user_script_dir}/{user_script}"
    content = dedent(
        f"""\
        [Unit]
        Description=Open {terminal} {run_script} on login
        After=graphical-session.target

        [Service]
        Type=oneshot
        ExecStartPre=/usr/bin/sleep 5
        ExecStart=/usr/bin/{terminal} python {run_script}
        Restart=no

        [Install]
        WantedBy=graphical-session.target
        """
    )
    dir_path = f"home/{user}/.config/systemd/user"
    name = f"{user_script.rsplit('.', 1)[0]}.service"
    copy_it(current_script_dir, (installation.target / user_script_dir))
    (installation.target / dir_path / name).write_text(content)
    installation.arch_chroot(f"chown {user}:{user} /{dir_path}/{name}")
    unit = UserService(
        source=f"/{dir_path}",
        target="graphical-session",
        services=[name],
    )
    enable_user_serv(installation, unit, user)


def mpd_tmpfiles(installation: Installer, user: str) -> None:
    cache = f"home/{user}/.cache/"
    dir_path = installation.target / cache / "mpd/playlists"
    dir_path.mkdir(parents=True, exist_ok=True)
    dir_path.chmod(0o755)
    installation.arch_chroot(f"chown -R {user}:{user} /{cache}")


###################################
# USR_SVC
###################################
def aur_and_remove_root(
    installation: Installer,
    users: list[User],
    sudo_default: list[str] | None = None,
) -> None:
    def write_sudoers(pword_require: str, user_name: str) -> None:
        write_data = [f"{user_name} ALL=(ALL:ALL) {pword_require}"]
        if sudo_default:
            write_data += "\n".join(f"Defaults    {line}" for line in sudo_default)
        sudoers_file = installation.target / f"etc/sudoers.d/00_{user_name}"
        sudoers_file.write_text("\n".join(write_data))

    def find_sudo_user() -> str | None:
        for user in users:
            if user.sudo:
                sudo_user = user.username
            for g in user.groups:
                if g == "wheel":
                    sudo_user = user.username
        return sudo_user

    sudo_user = find_sudo_user()
    if sudo_user:
        write_sudoers("NOPASSWD:ALL", sudo_user)
        log.info(f"Removed pass requirement for {sudo_user}")
        installation.arch_chroot(
            cmd=f"paru -S --noconfirm --needed {' '.join(aur_pkgs)}",
            run_as=sudo_user,
        )
        installation.arch_chroot(cmd="sudo passwd -dl root", run_as=sudo_user)
        write_etc_file(
            mnt_point=installation.target,
            files_to_write={
                "etc/ssh/sshd_config.d/20-deny_root.conf": "PermitRootLogin no\n"
            },
        )
        write_sudoers("ALL", sudo_user)
        log.info(f"Created pass requirement for {sudo_user}")


def auto_add_user_groups(
    installation: Installer,
    username: str,
    base_pkgs: list[str],
    pkg_groups={
        "realtime-privileges": "realtime",
        "android-udev": "adbusers",
        "scrcpy": "adbusers",
        "gnome-logs": "adm",
    },
) -> None:
    groups = []
    for pkg, group in pkg_groups.items():
        if pkg in base_pkgs and group not in groups:
            groups.append(group)
    if not groups:
        return
    group_str = groups[0] if len(groups) == 1 else ",".join(groups)
    installation.arch_chroot(f"usermod -aG {group_str} {username}")


# ==============================================================================
# 1. LIMINE CONFIGURATION
# ==============================================================================
def write_limine_opt(
    installation: Installer, filename: str, kernel_params: str, run_refresh: bool = True
) -> None:
    """Writes a kernel command line option to limine-entry-tool configuration."""
    output_dir = installation.target / "etc" / "limine-entry-tool.d"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / f"{filename}.conf"
    target_file.write_text(f"KERNEL_CMDLINE[default]+={kernel_params}\n")
    log.info(f"Wrote extra option '{kernel_params}' to {target_file}")
    if run_refresh:
        installation.arch_chroot("limine-mkinitcpio")


def set_default_cmdline(installation: Installer) -> None:
    limine_conf = installation.target / "boot" / "EFI" / "arch-limine" / "limine.conf"
    if not limine_conf.exists():
        log.warning(f"Limine configuration file not found at {limine_conf}")
        cmdline = ""
    for line in limine_conf.read_text().splitlines():
        line = line.strip()
        if line.startswith("cmdline:"):
            cmdline = line.split(":", 1)[1].strip()
            log.info(f"Retrieved cmdline: {cmdline}")
    write_limine_opt(installation, "original_flags", cmdline, run_refresh=True)


def set_boot_default(mountpoint: Path) -> None:
    limine_conf = mountpoint / "boot" / "limine.conf"
    if not limine_conf.exists():
        log.warning(f"Limine configuration file not found at {limine_conf}")
        return
    theme = [
        "interface_branding:",
        "term_palette: 21222c;ff5555;00ff99;f1fa8c;0072ff;ff79c6;33ccff;bfbfbf",
        "term_palette_bright: 4d4d4d;ff6e6e;10b981;ffffa5;a5b4fc;ff92df;a4ffff;ffffff",
        "term_background: 101013",
        "term_foreground: f4f5f6",
        "term_background_bright: 4d4d4d",
        "term_foreground_bright: white",
        "interface_branding_color: 0072ff",
        "interface_help_color: 0072ff",
        "interface_help_color_bright: a5b4fc",
    ]
    new_lines = []
    for line in limine_conf.read_text().splitlines():
        if line.strip().startswith("timeout:"):
            new_lines.extend(["timeout: 1", "remember_last_entry: yes"])
            continue
        new_lines.append(line)
        if line.strip() == "### Theme":
            new_lines.extend(theme)
    limine_conf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    log.info(f"Updated config parameters inside {limine_conf}")


def set_etc_default(mnt: Path) -> None:
    default_limine = mnt / "etc" / "default" / "limine"
    copy_it(mnt / "etc" / "limine-entry-tool.conf", default_limine)
    if not default_limine.exists():
        return
    content = default_limine.read_text().splitlines()
    for i, line in enumerate(content):
        if line.strip().startswith("#TARGET_OS_NAME"):
            content[i] = "TARGET_OS_NAME='Arch Linux'"
            break
    default_limine.write_text("\n".join(content) + "\n")


def limine_post(installation: Installer) -> None:
    installation.add_additional_packages("limine-mkinitcpio-hook")
    set_boot_default(installation.target)
    set_etc_default(installation.target)
    set_default_cmdline(installation)


# ==============================================================================
# 2. SUBSYSTEM MODULES
# ==============================================================================
def inst_apparmor(installation: Installer) -> None:
    installation.add_additional_packages(["apparmor", "apparmor.d-git"])
    write_limine_opt(
        installation,
        filename="apparmor",
        kernel_params="lsm=landlock,lockdown,yama,integrity,apparmor,bpf",
        run_refresh=False,
    )
    write_etc_file(
        mnt_point=installation.target,
        files_to_write={
            "etc/apparmor/parser.conf": dedent(
                """\
                write-cache
                cache-loc /etc/apparmor/earlypolicy/
                """
            )
        },
    )
    installation.enable_service("apparmor")


def inst_plymouth(installation: Installer) -> None:
    installation.add_additional_packages("plymouth")
    write_limine_opt(
        installation,
        filename="plymouth",
        kernel_params="quiet splash",
        run_refresh=False,
    )
    modify_mkinit(
        installation.target,
        hook="plymouth",
        after_hook="kms",
    )


def noah_install(
    installation: Installer,
    config: ArchConfig,
    nc: NoahConfig,
    script_d: Path,
) -> None:
    if config.swap and config.swap.enabled:
        write_etc_file(
            mnt_point=installation.target,
            files_to_write={
                "etc/systemd/zram-generator.conf": dedent(
                    """\
                    [zram0]
                    zram-size = min(ram / 2, 8192)
                    compression-algorithm = zstd
                    """
                ),
                "etc/sysctl.d/99-zram.conf": dedent(
                    """\
                    vm.swappiness = 180
                    vm.watermark_boost_factor = 0
                    vm.watermark_scale_factor = 125
                    vm.page-cluster = 0
                    vm.dirty_writeback_centisecs = 1500
                    """
                ),
            },
        )
    # app_and_profile
    profile_handler.install_greeter(installation, GreeterType.Ly)
    replace_ly_config(installation.target)
    sys_info = SysInfo()
    if sys_info.has_amd_graphics():
        profile_handler.install_gfx_driver(installation, GfxDriver.AmdOpenSource)
    if sys_info.has_nvidia_graphics():
        install_nvidia(installation)
        if sys_info.has_battery():
            installation.enable_service("nvidia-persistenced")
    if conf := config.app_config:
        if conf.power_management_config:
            if conf.power_management_config.power_management == PowerManagement.TUNED:
                tuned_post(installation)
        if firewall_conf := conf.firewall_config:
            if firewall_conf.firewall == Firewall("ufw"):
                ufw_post(installation, ["KDEConnect", "Deluge", "51820/udp"])
    # bootloader
    boot_conf = config.bootloader_config
    if boot_conf:
        if boot_conf.bootloader == Bootloader.Limine and not boot_conf.uki:
            limine_post(installation)
            inst_apparmor(installation)
            inst_plymouth(installation)
            log.info("Refreshing limine-mkinitcpio hooks cleanly.")
            installation.arch_chroot("limine-mkinitcpio")
    # bootloader
    # custom apps
    inst_systemd_oomd(installation)
    install_powertop(installation)
    write_etc_file(installation.target, network_files)
    write_etc_file(installation.target, etc_files_to_write)
    kde_fuse_and_nss(installation.target)
    if nc.firefox_browser:
        set_extensions(installation.target, nc.firefox_browser)
    sys_file_copy(installation.target, script_d)
    install_icons(installation)
    if nc.logitech_mouse:
        install_logid(installation, script_d)
    # custom apps
    # Noah disk
    if disk_config := config.disk_config:
        if disk_config.has_default_btrfs_vols():
            btrfs_options = disk_config.btrfs_options
            if btrfs_options:
                if auth_conf := config.auth_config:
                    if users := auth_conf.users:
                        snapper_post(installation, users)
            srvcs = ["btrfs-scrub@-.timer", "btrfs-scrub@home.timer"]
            installation.enable_service(srvcs)
    # Noah disk
    aur_and_remove_root(installation, users, nc.sudo_defaults)
    create_automount(installation, users)
    if auth_conf := config.auth_config:
        if users := auth_conf.users:
            for user in users:
                if nc.copy_config:
                    nc.copy_config.copy_root_to_mnt(installation.target, user.username)
                auto_add_user_groups(installation, user.username, config.packages)
                installation.arch_chroot("xdg-user-dirs-update", user.username)
                if nc.apps_to_hide:
                    hide_apps(installation, user.username, nc.apps_to_hide)
                user_service(installation, user.username, nc.terminal, script_d)
                mpd_tmpfiles(installation, user.username)
                if serv_conf := nc.user_services_config:
                    if srvcs := serv_conf.services:
                        for serv in srvcs:
                            enable_user_serv(installation, serv, user.username)
                installation.arch_chroot(
                    f"chown -R {user.username}:{user.username} /home/{user.username}"
                )
            installation.arch_chroot("chown -R root:root /usr/lib/systemd/user")
    if disable_svcs := nc.disable_svcs:
        installation.disable_service(disable_svcs)
    if mask_svcs := nc.disable_svcs:
        installation.arch_chroot(f"systemctl mask {' '.join(mask_svcs)}")
