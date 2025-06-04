#!/bin/bash

# Script to mount K-Pop external drives
# This script will mount three external drives to specific directories in the home folder
# Requires sudo privileges (configured via /etc/sudoers.d/kpop-mount-nopasswd for passwordless operation)

# Set error handling (but continue on individual mount failures)
set -u

# Define the home directory (handle sudo context)
if [ -n "$SUDO_USER" ]; then
    HOME_DIR="/home/$SUDO_USER"
else
    HOME_DIR="$HOME"
fi

# Define mount points
MOUNT_POINT_F="$HOME_DIR/windows_f_drive"
MOUNT_POINT_G="$HOME_DIR/windows_g_drive"
MOUNT_POINT_H="$HOME_DIR/windows_h_drive"

# Define drive labels
DRIVE_LABEL_F="kpop performances 2"
DRIVE_LABEL_G="kpop MV"
DRIVE_LABEL_H="kpop performances 1"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to create mount point if it doesn't exist
create_mount_point() {
    local mount_point="$1"
    if [ ! -d "$mount_point" ]; then
        log_message "Creating mount point: $mount_point"
        mkdir -p "$mount_point"
    fi
}

# Function to check if drive is already mounted
is_mounted() {
    local mount_point="$1"
    mount | grep -q "$mount_point"
}

# Function to find device by label
find_device_by_label() {
    local label="$1"
    # Try different methods to find the device
    local device=""
    
    # Method 1: Using blkid
    device=$(blkid -L "$label" 2>/dev/null || true)
    if [ -n "$device" ]; then
        echo "$device"
        return 0
    fi
    
    # Method 2: Using lsblk
    device=$(lsblk -rno NAME,LABEL | grep "$label" | awk '{print "/dev/"$1}' | head -1 || true)
    if [ -n "$device" ]; then
        echo "$device"
        return 0
    fi
    
    # Method 3: Check /dev/disk/by-label/
    if [ -L "/dev/disk/by-label/$label" ]; then
        readlink -f "/dev/disk/by-label/$label"
        return 0
    fi
    
    return 1
}

# Function to mount a drive
mount_drive() {
    local label="$1"
    local mount_point="$2"
    
    log_message "Attempting to mount '$label' at '$mount_point'"
    
    # Check if already mounted
    if is_mounted "$mount_point"; then
        log_message "Drive '$label' is already mounted at '$mount_point'"
        return 0
    fi
    
    # Create mount point
    create_mount_point "$mount_point"
    
    # Find device
    local device
    device=$(find_device_by_label "$label")
    if [ -z "$device" ]; then
        log_message "ERROR: Could not find device for label '$label'"
        return 1
    fi
    
    log_message "Found device '$device' for label '$label'"
    
    # Determine filesystem type
    local fstype
    fstype=$(blkid -o value -s TYPE "$device" 2>/dev/null || echo "auto")
    
    # Mount options based on filesystem type
    local mount_options=""
    case "$fstype" in
        "ntfs"|"exfat"|"vfat")
            mount_options="-o uid=$(id -u),gid=$(id -g),umask=022,rw"
            ;;
        *)
            mount_options="-o rw"
            ;;
    esac
    
    # Mount the drive
    if mount $mount_options "$device" "$mount_point"; then
        log_message "Successfully mounted '$label' ($device) at '$mount_point'"
        # Set permissions to ensure accessibility
        chmod 755 "$mount_point" 2>/dev/null || true
        return 0
    else
        log_message "ERROR: Failed to mount '$label' ($device) at '$mount_point'"
        return 1
    fi
}

# Main execution
log_message "Starting K-Pop drives mounting process"

# Check if running as root (required for mounting)
if [ "$EUID" -ne 0 ]; then
    log_message "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Track successful mounts
successful_mounts=0
total_drives=3

# Mount each drive
if mount_drive "$DRIVE_LABEL_F" "$MOUNT_POINT_F"; then
    ((successful_mounts++))
fi

if mount_drive "$DRIVE_LABEL_G" "$MOUNT_POINT_G"; then
    ((successful_mounts++))
fi

if mount_drive "$DRIVE_LABEL_H" "$MOUNT_POINT_H"; then
    ((successful_mounts++))
fi

# Summary
log_message "Mount operation completed: $successful_mounts/$total_drives drives mounted successfully"

if [ "$successful_mounts" -eq "$total_drives" ]; then
    log_message "All K-Pop drives mounted successfully"
    exit 0
elif [ "$successful_mounts" -gt 0 ]; then
    log_message "Some drives mounted successfully, but not all"
    exit 0
else
    log_message "No drives were mounted successfully"
    exit 1
fi
