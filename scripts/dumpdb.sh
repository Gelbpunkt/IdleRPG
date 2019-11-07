#!/bin/bash
echo "Removing old schema..."
rm schema.sql
touch schema.sql
echo "Dumping database $1..."
podman exec $1 pg_dump -U postgres $2 --schema-only > schema.sql.tmp
echo "Adding license header..."
cat <(cat assets/licenses/agpl_header_sql.txt) schema.sql.tmp > schema.sql
rm schema.sql.tmp
