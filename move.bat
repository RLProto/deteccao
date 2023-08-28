@echo off
setlocal

REM Define the source directory inside the Docker volume
set SOURCE_DIR=\\wsl.localhost\docker-desktop-data\data\docker\volumes\deteccao_g1

REM Define the destination directory on the Windows host
set DEST_DIR=C:\Python\venv\data

REM Use robocopy to move the files (robocopy will also copy subdirectories)
robocopy "%SOURCE_DIR%" "%DEST_DIR%" /MOVE

echo Files moved successfully!

endlocal