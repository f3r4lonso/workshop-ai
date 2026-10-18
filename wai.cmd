@echo off
rem Workshop AI launcher: runs the tool from this folder, in the current directory.
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m workshop_ai %*
