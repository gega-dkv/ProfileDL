#!/bin/sh
# 'Shortcut Input' should be the job ID, delivered via stdin.
read -r JOB_ID
case "$JOB_ID" in (*[!a-f0-9]*|'') echo '{"error":"Invalid job id"}'; exit 1;; esac
/Users/YOUR_USER/profiledl-starter/.venv/bin/python /Users/YOUR_USER/profiledl-starter/profiledl.py status "$JOB_ID"
