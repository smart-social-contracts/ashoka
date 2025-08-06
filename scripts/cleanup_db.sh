#!/bin/bash

# Database cleanup script for Ashoka tests
# Truncates the conversations table to ensure clean test environment

echo "Cleaning up database..."

PGPASSWORD=ashoka_pass psql -h localhost -p 5432 -U ashoka_user -d ashoka_db -c "TRUNCATE public.conversations RESTART IDENTITY;"

if [ $? -eq 0 ]; then
    echo "Database cleanup completed successfully"
    exit 0
else
    echo "Database cleanup failed"
    exit 1
fi
