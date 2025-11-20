# Backups Folder

This folder contains automatic backups of critical data.

## Contents

- Configuration backups (config_YYYYMMDD.json)
- Learned data backups (learned_YYYYMMDD.tar.gz)

## Automatic Backups

The application automatically creates backups:
- Daily backups of configuration
- Weekly backups of learned data
- Keeps last 10 backups

## Manual Backup

You can manually backup by copying files from:
- user_data/config/
- user_data/learned/
