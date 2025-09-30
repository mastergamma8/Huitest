#!/usr/bin/env bash
set -e
export $(grep -v '^#' .env | xargs) || true
python bot.py
