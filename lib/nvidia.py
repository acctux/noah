from archinstall.lib.installer import Installer
from textwrap import dedent
from utils import write_etc_file


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


def install_powertop(installation: Installer):
    packages = ["powertop"]
    installation.add_additional_packages(packages)
    nvidia_files: dict[str, str] = {
        "etc/systemd/system/powertop.service": dedent(
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
    }
    write_etc_file(installation.target, nvidia_files)
    installation.enable_service(packages)
