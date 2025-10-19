#######################################
# Logging helpers
#######################################
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
info() { printf "${BLUE}[INFO]${NC} %s\n" "$*" | tee -a "$LOG_FILE"; }
success() { printf "${GREEN}[SUCCESS]${NC} %s\n" "$*" | tee -a "$LOG_FILE"; }
warning() { printf "${YELLOW}[WARNING]${NC} %s\n" "$*" | tee -a "$LOG_FILE"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$*" | tee -a "$LOG_FILE"; }

fatal() {
	error "$*"
	exit 1
}

error_trap() {
	local exit_code=$?
	local line="$1"
	local cmd="$2"
	error "Command '${cmd}' failed at line ${line} with exit code ${exit_code}"
	exit "$exit_code"
}

#######################################
# Pre-flight checks
#######################################
require_root() {
	if [[ "$EUID" -ne 0 ]]; then
		fatal "This script must be run as root"
	fi
}

check_dependencies() {
	local deps=(lsblk curl sgdisk partprobe pacstrap arch-chroot numfmt)
	for cmd in "${deps[@]}"; do
		if ! command -v "$cmd" >/dev/null 2>&1; then
			fatal "Required command '$cmd' not found"
		fi
	done
}

yes_no_prompt() {
	# Ask a yes/no question until the user enters y or n
	local prompt="$1"
	local reply
	while true; do
		if ! read -rp "$prompt [y/n]: " reply; then
			fatal "Input aborted"
		fi
		case "$reply" in
		[Yy]) return 0 ;;
		[Nn]) return 1 ;;
		esac
		warning "Please answer 'y' or 'n'."
	done
}

get_country_iso() {
	local iso
	iso=$(curl -4 -s ifconfig.co/country-iso)

	if [ -z "$iso" ]; then
		# Fall back to LOCALE if curl fails
		iso=${LOCALE#*_} # Strip up to underscore -> e.g. "US.UTF-8"
		iso=${iso%%.*}   # Strip from dot onward -> e.g. "US"
	fi

	printf '%s\n' "$iso"
}

function pacman_install() {
	local -a packages=("$@")
	local success=false

	for attempt in {1..5}; do
		if pacman -Syu --noconfirm --needed "${packages[@]}"; then
			success=true
			break
		else
			echo "Attempt $attempt failed. Retrying in 10 seconds..."
			sleep 10
		fi
	done

	if [ "$success" = false ]; then
		echo "Installation failed after 5 attempts."
		exit 1
	fi
}

ask_password() {
  read -r -sp "Type User password: " PASSWORD1
  echo ""
  read -r -sp "Retype User password: " PASSWORD2
  echo ""
  if [[ "$PASSWORD1" == "$PASSWORD2" ]]; then
    SWORDPAS="$PASSWORD1"
  else
    echo "Password don't match. Please, type again."
    ask_password
  fi
}

check_install_commands() {
  local install_cmds=(
    arch-chroot
    findmnt
    genfstab
    lvcreate
    mount
    pacstrap
    partprobe
    pvcreate
    rsync
    sed
    sgdisk
    umount
    vgcreate
  )
  local c
  for c in "${install_cmds[@]}"; do
    if ! command -v "${c}" >/dev/null 2>&1; then
      return 1
    fi
  done
}
