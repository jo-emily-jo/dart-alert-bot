#!/bin/bash
cd /Users/emily/dart-alert-bot
source venv/bin/activate
python dart_alert_bot.py >> bot_log.txt 2>&1