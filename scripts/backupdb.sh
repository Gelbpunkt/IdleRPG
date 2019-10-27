#!/bin/bash
if [ -z "$1" ]
  then
    echo "No database name supplied"
    exit 1
fi
echo "Dumping database $1..."
podman exec postgresql pg_dump -U postgres $1 > backup.sql
