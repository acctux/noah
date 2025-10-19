#!/bin/bash

REPO_URL="https://github.com/acctux/fresh.git"
CLONE_DIR="$HOME/fresh"

REQUIRED_PACKAGES=(
	git
	arch-install-scripts
	bc
	curl
	dosfstools
	findutils
	gptfdisk
	grep
	pacman
	pacman-contrib
	pacman-mirrorlist
	parted
	rsync
	sed
)

clone_repo() {
	echo "Cloning repository..."
	if git clone "$REPO_URL" "$CLONE_DIR"; then
		cd "$CLONE_DIR"
	else
		echo "Git clone failed."
		rm -rf "$CLONE_DIR"
		return 1
	fi
}

update_reflector() {
	iso=$(curl -4 -s ifconfig.co/country-iso)
	reflector \
		--country "${iso}" \
		--protocol https \
		--completion-percent 100 \
		--age 24 \
		--fastest 10 \
		--sort rate \
		--threads 5 \
		--download-timeout 5 \
		--save /etc/pacman.d/mirrorlist
}
update_reflector

setup_environment() {
	local tries=0
	local max_tries=10

	while ((tries < max_tries)); do
		echo "Attempt $((tries + 1)) of $max_tries..."

		# Ensure network is up
		if ! ping -c 1 archlinux.org &>/dev/null; then
			echo "Network unavailable. Retrying..."
			((tries++))
			sleep 5
			continue
		fi

		# Sync package database
		if ! pacman -Sy; then
			echo "pacman -Sy failed."
			((tries++))
			sleep 5
			continue
		fi

		# Initialize and populate pacman keyring
		if ! pacman-key --init; then
			echo "pacman-key --init failed."
			((tries++))
			sleep 5
			continue
		fi

		if ! pacman -S --noconfirm archlinux-keyring; then
			echo "Installing archlinux-keyring failed."
			((tries++))
			sleep 5
			continue
		fi

		# Install required packages
		if ! pacman -S --noconfirm --needed "${REQUIRED_PACKAGES[@]}"; then
			echo "Package installation failed."
			((tries++))
			sleep 5
			continue
		fi

		# Attempt to clone the repo
		if clone_repo; then
			return 0
		else
			((tries++))
			sleep 5
		fi
	done

	echo "All $max_tries attempts failed. Exiting."
	exit 1
}
setup_environment

s_pac_ed() {
	local pac_conf="/etc/pacman.conf"
	sed -i '/^\s*#\s*Color\s*$/s/^#\s*//' $pac_conf
	sed -i '/^\s*Color\s*$/a ILoveCandy' $pac_conf
	sed -i '/^\s*#\s*\[multilib\]/s/^#\s*//' $pac_conf
	sed -i '/^\[multilib\]/,/^$/{ /^\s*#\s*Include\s*=.*/s/^#\s*// }' $pac_conf
	sed -i '/ParallelDownloads/c\ParallelDownloads = 10' $pac_conf
}
s_pac_ed

cd ~/fresh
git checkout test

echo "Welcome to Noah's Arch, you'll be swept away."

chmod +x kat get-chrooted noah
