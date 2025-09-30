#!/usr/bin/env bash
set -e
export $(grep -v '^#' .env | xargs) || true
uvicorn web.main:app --host 0.0.0.0 --port 8000
