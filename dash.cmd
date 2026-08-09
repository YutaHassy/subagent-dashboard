@echo off
rem Launcher for the agent dashboard (Windows).
rem Messages here are ASCII on purpose: .cmd files are read with the system code page.
rem
rem Exit code handling, learned the hard way:
rem   - "exit /b %errorlevel%" INSIDE a parenthesised if-block expands before the block runs
rem   - "setlocal" can reset ERRORLEVEL through its implicit endlocal
rem   - "goto :eof" did not preserve the code reliably either
rem So: no setlocal, no blocks. Each "exit /b %errorlevel%" sits on its own line
rem directly after the python call, where it expands at execution time.

where /q python
if errorlevel 1 goto try_py

python "%~dp0dash.py" %*
exit /b %errorlevel%

:try_py
where /q py
if errorlevel 1 goto no_python

py -3 "%~dp0dash.py" %*
exit /b %errorlevel%

:no_python
echo [dash] Python was not found on PATH.
echo [dash] Install Python 3.9 or later from https://www.python.org/ and try again.
exit /b 1
