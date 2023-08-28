@echo off
setlocal

REM Define the source directories inside the Docker volumes
set SOURCE_DIR1=\\wsl.localhost\docker-desktop-data\data\docker\volumes\deteccao_g1\_data
set SOURCE_DIR2=\\wsl.localhost\docker-desktop-data\data\docker\volumes\deteccao_g2\_data
set SOURCE_DIR3=\\wsl.localhost\docker-desktop-data\data\docker\volumes\deteccao_g3\_data
set SOURCE_DIR4=\\wsl.localhost\docker-desktop-data\data\docker\volumes\deteccao_g4\_data

REM Define the destination directory on the Windows host
set DEST_DIR=C:\Python\venv\data

REM Use robocopy to move the files from each source directory to the destination directory
robocopy "%SOURCE_DIR1%" "%DEST_DIR%" /MOV
robocopy "%SOURCE_DIR2%" "%DEST_DIR%" /MOV
robocopy "%SOURCE_DIR3%" "%DEST_DIR%" /MOV
robocopy "%SOURCE_DIR4%" "%DEST_DIR%" /MOV

echo Files moved successfully!

endlocal