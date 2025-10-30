#!/usr/bin/env python3
import os
import shutil
import subprocess

HIDE_APP_FILES = [
    "/usr/share/applications/avahi-discover.desktop",
    "/usr/share/applications/octopi-cachecleaner.desktop",
    "/usr/share/applications/avahi-discover.desktop",
    "/usr/share/applications/xgps.desktop",
    "/usr/share/applications/xgpsspeed.desktop",
    "/usr/share/applications/steam.desktop",
    "/usr/share/applications/qv4l2.desktop",
    "/usr/share/applications/qvidcap.desktop",
    "/usr/share/applications/bssh.desktop",
    "/usr/share/applications/bvnc.desktop",
    "/usr/share/applications/blueman-adapters.desktop",
    "/usr/share/applications/nm-connection-editor.desktop",
    "/usr/share/applications/org.kde.kdeconnect.sms.desktop",
    "/usr/share/applications/org.kde.kdeconnect.app.desktop",
    "/usr/share/applications/btop.desktop",
    "/usr/share/applications/org.gnome.FileRoller.desktop",
    "/usr/share/applications/org.pulseaudio.pavucontrol.desktop",
    "/usr/share/applications/qv4l2.desktop",
]

ICON_OVERRIDES = {
    "nwg-clipman": "xclipboard",
    "octopi.desktop": "alienarena",
    "com.ayugram.desktop.desktop": "telegram",
}


def hide_apps():
    """Append 'NoDisplay=true' to specified .desktop files."""
    print("Hiding apps")

    for file_path in HIDE_APP_FILES:
        basename = os.path.basename(file_path)
        if not os.path.isfile(file_path):
            print(f"{basename} not found.")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not any(line.strip() == "NoDisplay=true" for line in lines):
            lines.append("\nNoDisplay=true\n")
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"Hid {basename}")
        else:
            print(f"{basename} already hidden.")

    if shutil.which("update-desktop-database"):
        print("Updating desktop database...")
        subprocess.run(
            ["sudo", "update-desktop-database", "/usr/share/applications/"], check=False
        )


def change_icons():
    """Update the Icon= field in .desktop files using ICON_OVERRIDES."""
    print("Changing icons")

    for appname, new_icon in ICON_OVERRIDES.items():
        file_path = f"/usr/share/applications/{appname}.desktop"
        if not os.path.isfile(file_path):
            print(f"{appname}.desktop not found.")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        icon_updated = False
        for i, line in enumerate(lines):
            if line.startswith("Icon="):
                lines[i] = f"Icon={new_icon}\n"
                icon_updated = True
                break

        if not icon_updated:
            lines.append(f"Icon={new_icon}\n")

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"Updated icon for {appname} → {new_icon}")

    if shutil.which("update-desktop-database"):
        print("Updating desktop database...")
        subprocess.run(
            ["sudo", "update-desktop-database", "/usr/share/applications/"], check=False
        )


if __name__ == "__main__":
    hide_apps()
    change_icons()
