#!/bin/bash

REPO="acctux/noah"
CLONE_DIR="$HOME/archinstall"
DEPENDENCIES=("git" "pacman-contrib")

setup_environment() {
  local tries=0
  local max_tries=5
  while ((tries < max_tries)); do
    if ! pacman-key --init; then
      echo "pacman-key --init failed."
      ((tries++))
      sleep 5
      continue
    fi
    if ! pacman -Sy --noconfirm; then
      echo "pacman -Sy failed."
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
    if ! pacman -S --noconfirm --needed "${DEPENDENCIES[@]}"; then
      echo "Package installation failed."
      ((tries++))
      sleep 5
      continue
    fi
    echo "Environment setup successful."
    return 0
  done
  echo "All $max_tries attempts failed. Exiting."
  exit 1
}

clone_repo() {
  rm -rf "$CLONE_DIR"
  echo "Cloning repository..."
  if git clone "https://github.com/${REPO}.git" "$CLONE_DIR"; then
    echo "Repository cloned successfully."
  else
    echo "Git clone failed."
    exit 1
  fi
}

setup_environment
clone_repo
echo "Initial setup complete. Run './archinstall/sys_setup.py'"
exec python /root/archinstall/sys_setup.py </dev/tty
