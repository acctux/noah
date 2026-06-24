from textwrap import dedent
import json
from lib.datahandler import NoahConfig
from utils import log, copy_it, write_etc_file
import shutil
from archinstall.lib.installer import Installer
from pathlib import Path


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


def handle_cust_apps(installation: Installer, nc: NoahConfig, script_d: Path):
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
