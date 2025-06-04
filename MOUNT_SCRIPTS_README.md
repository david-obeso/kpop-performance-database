# K-Pop Drive Mount Scripts Setup

## Overview
These scripts automatically mount and unmount the three K-Pop external drives when the application starts and stops.

## Drive Mapping
- **"kpop performances 2"** → `~/windows_f_drive`
- **"kpop MV"** → `~/windows_g_drive` 
- **"kpop performances 1"** → `~/windows_h_drive`

## Sudo Configuration
The scripts require sudo privileges but are configured to run without password prompts via:
`/etc/sudoers.d/kpop-mount-nopasswd`

## Scripts
- `mount_kpop_drives.sh` - Called at application startup
- `unmount_kpop_drives.sh` - Called at application shutdown

## Features
- Automatic drive detection by label using blkid and lsblk
- Safe unmounting with process termination if needed
- Comprehensive error handling and logging with timestamps
- Support for various filesystem types (NTFS, ExFAT, etc.)
- Continues mounting other drives even if one fails
- Proper handling of sudo context (uses original user's home directory)

## Security Notes
- Only specific mount/unmount commands are allowed without password
- Scripts are restricted to the exact paths configured
- No general sudo privileges are granted

## Status
✅ **TESTED AND WORKING** - Both scripts successfully mount and unmount all three drives

## Troubleshooting
- Check the script output for detailed error messages and timestamps
- The scripts will report exactly which drives were successfully mounted/unmounted
- If drives are already mounted elsewhere, the scripts will detect and handle this
- Scripts use lazy unmounting (-l) by default for safer drive removal
