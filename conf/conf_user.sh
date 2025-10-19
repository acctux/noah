#######################################
# Groups/Services
#######################################
TO_DEF="fresh"
TIMEZONE="US/Eastern"
HOST_NAME="yulia"
USER_NAME="nick"
LOCALE="en_US.UTF-8"
DEFAULT_EFI_SIZE="512MiB"
BOOTLOADER="systemd-boot"
ROOT_LABEL="Arch"
KEY_DIR=".ssh"
KEYMAP="us"
MOUNT_OPTIONS="noatime,compress=zstd"

#######################################
# Git
#######################################
GIT_USER="acctux"
DOT_URL="https://github.com/acctux/dotfiles.git"
GIT_DIR="Lit"
DOT_DIR="dotfiles"
GIT_REPOS=(
	"docs"
	"dotfiles"
	"fresh"
	"freshpy"
	"post"
)

#######################################
# Keys
#######################################
SSH_KEYFILE="id_ed25519"
GPG_KEYFILE="my-private-key.asc"
MY_PASS="pass.asc"
KEY_FILES=(
	"$SSH_KEYFILE"
	"$GPG_KEYFILE"
	"$MY_PASS"
)

#######################################
# Groups/Services
#######################################
USER_GROUPS=(
	wheel
	power
	input
	audio
	video
	network
	storage
	rfkill
	log
	games
	gamemode
)

#######################################
# Sysd services
#######################################
SYSD_ENABLE=(
	acpid.service
	ananicy-cpp.service
	avahi-daemon.service
	bluetooth.service
	logid.service
	ly.service
	NetworkManager.service
	ntpd.service
	personal-powertop.service
	tlp.service
	fstrim.timer
	logrotate.timer
	man-db.timer
	paccache.timer
	reflector.timer
)

SYSD_DISABLE=(
	systemd-timesyncd
)

#######################################
# User services
#######################################
USER_SERV_ENABLE=(
	gnome-keyring-daemon.service
	hypridle.service
	hyprpolkitagent.service
	mako.service
	pipewire.service
	pipewire-pulse.service
	wireplumber.service
	waybar.service
	wallpaper.timer
	gcr-ssh-agent.socket
)

#######################################
# Folders
#######################################
BOOKMARKS="/home/$USER_NAME/.local/bin/bookmarks"

CUSTOM_FOLDERS=(
	["$HOME/Games"]="folder-games"
	["$HOME/Lit"]="folder-github"
	["$BOOKMARKS"]="folder-favorites"
)

REMOVE_XDG_DIRS=(
	"XDG_PUBLICSHARE_DIR"
	"XDG_DOCUMENTS_DIR"
	"XDG_DESKTOP_DIR"
)

CUSTOM_XDG_ENTRIES=(
	"XDG_LIT_DIR=$GIT_DIR"
	"XDG_BOOKMARKS_DIR=$BOOKMARKS"
)
