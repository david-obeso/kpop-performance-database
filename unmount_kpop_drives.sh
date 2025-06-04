#!/bin/bash

# Script to unmount K-Pop external drives
# This script will safely unmount the three K-Pop external drives
# Requires sudo privileges (configured via /etc/sudoers.d/kpop-mount-nopasswd for passwordless operation)

# Set error handling (but continue on individual unmount failures)
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

# Define drive labels for reference
DRIVE_LABEL_F="kpop performances 2"
DRIVE_LABEL_G="kpop MV"
DRIVE_LABEL_H="kpop performances 1"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if drive is mounted
is_mounted() {
    local mount_point="$1"
    mount | grep -q "$mount_point"
}

# Function to safely unmount a drive
unmount_drive() {
    local mount_point="$1"
    local label="$2"
    
    log_message "Attempting to unmount '$label' from '$mount_point'"
    
    # Check if mounted
    if ! is_mounted "$mount_point"; then
        log_message "Drive '$label' is not mounted at '$mount_point'"
        return 0
    fi
    
    # Try to sync before unmounting
    log_message "Syncing filesystem for '$label'"
    sync
    
    # Attempt lazy unmount first (safer)
    if umount -l "$mount_point" 2>/dev/null; then
        log_message "Successfully unmounted '$label' from '$mount_point' (lazy unmount)"
        return 0
    fi
    
    # If lazy unmount failed, try regular unmount
    log_message "Lazy unmount failed, trying regular unmount for '$label'"
    if umount "$mount_point" 2>/dev/null; then
        log_message "Successfully unmounted '$label' from '$mount_point'"
        return 0
    fi
    
    # If regular unmount failed, try force unmount
    log_message "Regular unmount failed, trying force unmount for '$label'"
    if umount -f "$mount_point" 2>/dev/null; then
        log_message "Successfully force unmounted '$label' from '$mount_point'"
        return 0
    fi
    
    # Check what processes might be using the mount point
    log_message "Checking for processes using '$mount_point'"
    local processes
    processes=$(lsof +D "$mount_point" 2>/dev/null | tail -n +2 | awk '{print $2}' | sort -u || true)
    
    if [ -n "$processes" ]; then
        log_message "WARNING: The following processes are still using '$mount_point': $processes"
        log_message "You may need to close applications using these files before unmounting"
    fi
    
    log_message "ERROR: Failed to unmount '$label' from '$mount_point'"
    return 1
}

# Function to check and kill processes using mount points (emergency)
kill_processes_using_mount() {
    local mount_point="$1"
    local label="$2"
    
    log_message "Attempting to terminate processes using '$mount_point' for '$label'"
    
    # Get PIDs of processes using the mount point
    local pids
    pids=$(lsof +D "$mount_point" 2>/dev/null | tail -n +2 | awk '{print $2}' | sort -u || true)
    
    if [ -n "$pids" ]; then
        log_message "Found processes using '$mount_point': $pids"
        
        # First try SIGTERM
        for pid in $pids; do
            if kill -TERM "$pid" 2>/dev/null; then
                log_message "Sent SIGTERM to process $pid"
            fi
        done
        
        # Wait a moment
        sleep 2
        
        # Check if processes are still running and use SIGKILL if necessary
        local remaining_pids
        remaining_pids=$(lsof +D "$mount_point" 2>/dev/null | tail -n +2 | awk '{print $2}' | sort -u || true)
        
        if [ -n "$remaining_pids" ]; then
            log_message "Some processes still running, sending SIGKILL"
            for pid in $remaining_pids; do
                if kill -KILL "$pid" 2>/dev/null; then
                    log_message "Sent SIGKILL to process $pid"
                fi
            done
            sleep 1
        fi
    fi
}

# Function to emergency unmount (with process termination)
emergency_unmount() {
    local mount_point="$1"
    local label="$2"
    
    log_message "Attempting emergency unmount for '$label'"
    
    # Kill processes using the mount point
    kill_processes_using_mount "$mount_point" "$label"
    
    # Try unmounting again
    if umount -f "$mount_point" 2>/dev/null; then
        log_message "Emergency unmount successful for '$label'"
        return 0
    else
        log_message "Emergency unmount failed for '$label'"
        return 1
    fi
}

# Main execution
log_message "Starting K-Pop drives unmounting process"

# Check if running as root (required for unmounting)
if [ "$EUID" -ne 0 ]; then
    log_message "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Track successful unmounts
successful_unmounts=0
total_mounted=0

# Count how many drives are actually mounted
for mount_point in "$MOUNT_POINT_F" "$MOUNT_POINT_G" "$MOUNT_POINT_H"; do
    if is_mounted "$mount_point"; then
        ((total_mounted++))
    fi
done

if [ "$total_mounted" -eq 0 ]; then
    log_message "No K-Pop drives are currently mounted"
    exit 0
fi

log_message "Found $total_mounted K-Pop drives mounted"

# Unmount each drive
if unmount_drive "$MOUNT_POINT_F" "$DRIVE_LABEL_F"; then
    ((successful_unmounts++))
fi

if unmount_drive "$MOUNT_POINT_G" "$DRIVE_LABEL_G"; then
    ((successful_unmounts++))
fi

if unmount_drive "$MOUNT_POINT_H" "$DRIVE_LABEL_H"; then
    ((successful_unmounts++))
fi

# Summary
log_message "Unmount operation completed: $successful_unmounts/$total_mounted drives unmounted successfully"

if [ "$successful_unmounts" -eq "$total_mounted" ]; then
    log_message "All mounted K-Pop drives unmounted successfully"
    exit 0
elif [ "$successful_unmounts" -gt 0 ]; then
    log_message "Some drives unmounted successfully, but not all"
    
    # For any remaining mounted drives, show what's still mounted
    log_message "Checking remaining mounted drives..."
    for mount_point in "$MOUNT_POINT_F" "$MOUNT_POINT_G" "$MOUNT_POINT_H"; do
        if is_mounted "$mount_point"; then
            log_message "WARNING: '$mount_point' is still mounted"
        fi
    done
    
    exit 1
else
    log_message "No drives were unmounted successfully"
    exit 1
fi
