from pathlib import Path
from archinstall.default_profiles.profile import GreeterType
from archinstall.lib.models.application import PowerManagement
from archinstall.lib.args import ArchConfig
from archinstall.lib.installer import Installer
from archinstall.lib.hardware import SysInfo, GfxDriver
from archinstall.lib.profile.profiles_handler import profile_handler
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


class NoahSysInfo:
    def __init__(self, sys_info: SysInfo):
        vendor = sys_info.cpu_vendor()
        self.nvidia: bool = sys_info.has_nvidia_graphics()
        self.cpu_vendor: str | None = getattr(vendor, "value", str(vendor))
        self.amd: bool = sys_info.has_amd_graphics()
        self.is_vm: bool = sys_info.is_vm()
        self.has_bat: bool = sys_info.has_battery()


def app_and_prof(installation: Installer, config: ArchConfig):
    profile_handler.install_greeter(installation, GreeterType.Ly)
    replace_ly_config(installation.target)
    sys_info = NoahSysInfo(SysInfo())
    if sys_info.amd:
        profile_handler.install_gfx_driver(installation, GfxDriver.AmdOpenSource)
    if sys_info.nvidia:
        install_nvidia(installation)
        if sys_info.has_bat:
            installation.enable_service("nvidia-persistenced")

    if config.app_config:
        if config.app_config.power_management_config:
            if (
                config.app_config.power_management_config.power_management
                == PowerManagement.TUNED
            ):
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
