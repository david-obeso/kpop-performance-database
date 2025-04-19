#!/bin/bash

# --- Configuration ---
WIN_IP="000.000.0.00"                  # <-- CHANGE: Your Windows PC's IP Address or Hostname
WIN_USER="*****"       # <-- CHANGE: Your Windows Username (can often be omitted if in credentials file)
CREDS_FILE="/home/******/.smbcredentials"      # Path to your credentials file

# Define Shares and corresponding Mount Points
# Format: "SHARE_NAME|MOUNT_POINT_SUFFIX"
SHARES=(
    "F|windows_f_drive"          # <-- CHANGE: Windows Share Name | Your Directory Name
    "G|windows_g_drive"          # <-- CHANGE: Windows Share Name | Your Directory Name
    "H|windows_h_drive"          # <-- CHANGE: Windows Share Name | Your Directory Name
)

# Capture the UID and GID of the user running the script
USER_UID=$(id -u)
USER_GID=$(id -g)

# Mount options
# uid/gid: Set file ownership to the user running the script
# vers=3.0: SMB protocol version (try 2.1 or 1.0 if 3.0 fails)
# iocharset=utf8: Handle special characters in filenames
# nounix: Disable POSIX extensions (often improves compatibility with Windows)
# file_mode/dir_mode: Set default permissions for files/dirs created from Linux
MOUNT_OPTS="credentials=$CREDS_FILE,uid=$USER_UID,gid=$USER_GID,vers=3.0,iocharset=utf8,nounix,file_mode=0770,dir_mode=0770"

# --- Script Logic ---
echo "Attempting to mount Windows shares from $WIN_IP..."

# Check if credentials file exists
if [ ! -f "$CREDS_FILE" ]; then
    echo "ERROR: Credentials file not found at $CREDS_FILE"
    echo "Please create it with your Windows username and password."
    exit 1
fi

# Check if cifs-utils is installed
if ! dpkg -s cifs-utils > /dev/null 2>&1; then
    echo "ERROR: 'cifs-utils' package not found."
    echo "Please install it using: sudo apt update && sudo apt install cifs-utils"
    exit 1
fi

# Loop through the shares and mount them
for share_info in "${SHARES[@]}"; do
    # Split the share name and mount point suffix
    IFS='|' read -r share_name mount_suffix <<< "$share_info"

    mount_point="/home/******/$mount_suffix"
    unc_path="//$WIN_IP/$share_name"

    echo "-------------------------------------"
    echo "Processing Share: $share_name"
    echo "Target Mount Point: $mount_point"

    # Create mount point directory if it doesn't exist
    mkdir -p "$mount_point"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create directory $mount_point. Check permissions."
        continue # Skip to the next share
    fi

    # Check if the directory is already a mount point
    if mountpoint -q "$mount_point"; then
        echo "INFO: Already mounted at $mount_point."
    else
        echo "Attempting to mount $unc_path ..."
        # The actual mount command - requires sudo
        sudo mount -t cifs "$unc_path" "$mount_point" -o "$MOUNT_OPTS"

        # Check if mount was successful
        if mountpoint -q "$mount_point"; then
            echo "SUCCESS: Mounted $share_name to $mount_point."
        else
            echo "ERROR: Failed to mount $share_name. Check:"
            echo "  - Network connection to $WIN_IP"
            echo "  - Share name '$share_name' is correct and shared on Windows"
            echo "  - Credentials in $CREDS_FILE are correct"
            echo "  - Windows Firewall allows File and Printer Sharing"
            echo "  - Try changing 'vers=' option in the script (e.g., vers=2.1)"
            # Optional: attempt to clean up directory if empty? Maybe not needed.
        fi
    fi
done

echo "-------------------------------------"
echo "Mount process finished."

exit 0

