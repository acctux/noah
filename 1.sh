#!/bin/bash

REPO_URL="https://github.com/acctux/noah.git"
CLONE_DIR="$HOME/archinstall"
DEPENDENCIES=("git" "pacman-contrib" "python-pyyaml")

setup_environment() {
  local tries=0
  local max_tries=5
  if [ -z "$ARCH_USER" ] || [ -z "$ARCH_PASS" ]; then
    echo "Error: use ARCH_USER=**** ARCH_PASS=****"
    exit 1
  fi
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
  if git clone "$REPO_URL" "$CLONE_DIR"; then
    echo "Repository cloned successfully."
  else
    echo "Git clone failed."
    exit 1
  fi
}

add_user() {
  JSON_FILE="$CLONE_DIR/user_config.json"
  username="$ARCH_USER"
  password="$ARCH_PASS"
  hashed_pass=$(openssl passwd -6 "$password")
  cat >"$JSON_FILE" <<EOF
{
  "users": [
    {
      "sudo": true,
      "username": "$username",
      "enc_password": "$hashed_pass"
    }
  ],
  "root_enc_password": "$hashed_pass"
}
EOF
  echo "JSON file created/overwritten successfully at $JSON_FILE"
}

setup_environment
clone_repo
add_user
echo "Download complete. Run 'python archinstall/sys_setup.py'"
