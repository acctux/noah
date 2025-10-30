#!/usr/bin/env bash

set -euo pipefail

#######################################
# # Sourcing # # # # # # # # # # # # #
#######################################
SCRIPT_D="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"
PKG_D="$SCRIPT_D/pkg"
USER_SCRIPTS="$SCRIPT_D/user/user-scripts"
LOG_FILE="$SCRIPT_D/log"

. "$SCRIPT_D/user-config"

#######################################
# Variable Sourcing
#######################################
. "$SCRIPT_D/utils"
. "$USER_SCRIPTS/user-icons.sh"
. "$USER_SCRIPTS/user-services.sh"
. "$USER_SCRIPTS/security-keys.sh"

#######################################
#  Main
#######################################
main() {
  trap 'error_trap $LINENO "$BASH_COMMAND"' ERR
  set -eEuo pipefail

  user_folders_icons

  info "cloning dotfiles"
  git clone "$DOT_URL" "$HOME/temp_dots"
  rsync -avh --no-perms --no-owner --no-group \
    --exclude ".git/" "$HOME/temp_dots/" "$HOME/"
  python "$USER_SCRIPTS/dotsync.py"
  enable_user_services

  paru -S ayugram-desktop-bin surfshark-client
  sudo firewall-cmd --set-default-zone=block
  sudo python "$USER_SCRIPTS/dotsync.py"

  import_ssh_keys
  import_gpg_key
  clone_gits

}
main "$@"
