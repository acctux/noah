import subprocess
import os
import re
import requests


def get_country_iso():
    """Detect the country ISO code."""
    try:
        response = requests.get("https://ifconfig.co/country-iso", timeout=3)
        iso = response.text.strip()
    except requests.RequestException:
        # Fallback: try to use locale environment variable
        locale = os.environ.get("LOCALE", "")
        iso = locale.split("_")[1] if "_" in locale else "US"
    return iso


def detect_cpu():
    """Detect CPU vendor (Intel or AMD)."""
    cpu_vendor = "intel"  # default
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
            if "GenuineIntel" in cpuinfo:
                cpu_vendor = "intel"
            elif "AuthenticAMD" in cpuinfo:
                cpu_vendor = "amd"
    except FileNotFoundError:
        pass
    return cpu_vendor


def detect_gpu():
    """Detect GPU vendor (Intel, AMD, NVIDIA)."""
    gpu_vendor = "unknown"
    try:
        gpu_info = subprocess.check_output(["lspci"], text=True)
        if re.search(r"(Radeon|AMD).*VGA", gpu_info):
            gpu_vendor = "amd"
        elif re.search(r"(NVIDIA|GeForce)", gpu_info):
            gpu_vendor = "nvidia"
        elif re.search(r"Intel.*(Tiger Lake|Alder Lake|Iris Xe|UHD)", gpu_info):
            gpu_vendor = "intel"
    except subprocess.SubprocessError:
        pass
    return gpu_vendor


# Example usage
if __name__ == "__main__":
    get_country_iso()
    detect_cpu()
    detect_gpu()
