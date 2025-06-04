#!/bin/bash
# Script to unmount K-pop USB drives by label
# Usage: sudo ./unmount_kpop_drives.sh

# Determine credentials file path
if [[ -n "$SUDO_USER" ]]; then
  # Script is run with sudo, try to find credentials in original user's home
  ORIGINAL_HOME=$(eval echo ~$SUDO_USER)
  CRED_FILE="$ORIGINAL_HOME/.kpop_mount_credentials"
  # Fallback to current user's home if not found in original user's home (e.g. if sudo -H is used or SUDO_USER is root)
  if [[ ! -f "$CRED_FILE" && "$HOME" != "$ORIGINAL_HOME" ]]; then
    ALT_CRED_FILE="$HOME/.kpop_mount_credentials"
    if [[ -f "$ALT_CRED_FILE" ]]; then
      CRED_FILE="$ALT_CRED_FILE"
    fi
  fi
elif [[ $(id -u) -eq 0 ]]; then
  # Script is run as root directly (not via sudo from a user)
  # In this case, $HOME is /root, so we expect credentials there or it should fail clearly.
  CRED_FILE="$HOME/.kpop_mount_credentials"
else
  # Script is run by user directly
  CRED_FILE="$HOME/.kpop_mount_credentials"
fi

# Load sudo password from credentials file
if [[ -f "$CRED_FILE" ]]; then
    source "$CRED_FILE"
    if [[ -z "$PASSWORD" ]]; then
        echo "Credentials file exists at '$CRED_FILE' but PASSWORD is empty. Please set PASSWORD." >&2
        exit 1
    fi
else
    echo "Credentials file not found. Checked: '$CRED_FILE'." >&2
    if [[ -n "$SUDO_USER" && "$ORIGINAL_HOME" != "$HOME" && "$CRED_FILE" != "$ORIGINAL_HOME/.kpop_mount_credentials" ]]; then
      echo "Also checked original user's potential path: '$ORIGINAL_HOME/.kpop_mount_credentials'." >&2
    elif [[ "$CRED_FILE" != "$HOME/.kpop_mount_credentials" ]]; then
      echo "Also checked current user's potential path: '$HOME/.kpop_mount_credentials'." >&2
    fi
    echo "Create the file with a single line: PASSWORD=your_sudo_password" >&2
    exit 1
fi

set -e

# Define label-directory pairs
declare -A drives=(
  ["kpop performances 1"]="/home/david/windows_f_drive"
  ["kpop MV"]="/home/david/windows_g_drive"
  ["kpop performances 2"]="/home/david/windows_h_drive"
)

for label in "${!drives[@]}"; do
  mount_point="${drives[$label]}"
  if mount | grep -q "on $mount_point "; then
    echo "Unmounting $mount_point ..."
    # Use sudo with provided password
    echo "$PASSWORD" | sudo -S umount "$mount_point"
    echo "Unmounted $mount_point."
  else
    echo "$mount_point is not mounted."
  fi
done
