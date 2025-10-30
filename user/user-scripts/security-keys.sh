import_ssh_keys() {
  ssh_path="$HOME/${KEY_DIR}/${SSH_KEYFILE}"
  local socket="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ssh-agent.socket"

  if [[ -z "${SSH_AUTH_SOCK:-}" ]]; then
    export SSH_AUTH_SOCK="$socket"
  fi

  if [[ ! -S "${SSH_AUTH_SOCK}" ]]; then
    systemctl --user enable --now ssh-agent.socket
  fi

  local key_fingerprint
  key_fingerprint=$(ssh-keygen -lf "${ssh_path}" | awk '{print $2}')

  if ssh-add -l 2>/dev/null | grep -q "${key_fingerprint}"; then
    info "SSH key already loaded in GCR SSH agent."
  else
    if ssh-add "${ssh_path}" 2>/dev/null; then
      info "$ssh_path successfully added to GCR SSH agent."
    else
      error "Failed to add SSH key to GCR SSH agent."
      return 1
    fi
  fi
}

import_gpg_key() {
  gpg_path="$HOME/${KEY_DIR}/${GPG_KEYFILE}"
  local fingerprint
  fingerprint=$(
    gpg --import-options show-only --import \
      --with-colons "${gpg_path}" 2>/dev/null |
      awk -F: '/^fpr:/ { print $10; exit }'
  )

  if ! gpg --list-keys "$fingerprint" &>/dev/null; then
    gpg --import "${gpg_path}"
    echo "${fingerprint}:6:" | gpg --import-ownertrust
    success "Imported GPG key $fingerprint."
  else
    info "GPG key $fingerprint already exists."
  fi
}
