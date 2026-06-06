@echo off
cd /d "%~dp0"
python -m pytest test_parser.py -v
pause
