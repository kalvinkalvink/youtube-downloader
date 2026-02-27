@echo off
REM Build script for YouTube Downloader with Automatic FFmpeg Download
REM
REM This script will:
setlocal enabledelayedexpansion

REM ====== READ VERSION FROM PYPROJECT.TOML ======
set APP_NAME=youtube-downloader

REM Read version from pyproject.toml
for /f "tokens=2 delims==" %%v in ('findstr /r "^version *=" "%~dp0pyproject.toml"') do set "APP_VERSION=%%v"
set "APP_VERSION=%APP_VERSION:"=%"


if not defined APP_VERSION (
    echo WARNING: Could not read version from pyproject.toml, using default 0.1.0
    set APP_VERSION=0.1.0
) else (
    echo Detected version: %APP_VERSION%
)
REM =============================================

REM ====== CONFIGURATION ======
set FFMPEG_ZIP=ffmpeg-master-latest-win64-gpl.zip
set FFMPEG_URL=https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip
set TEMP_DIR=%TEMP%\ffmpeg-download
REM ===========================

echo ========================================
echo YouTube Downloader Build Script
echo ========================================
echo.

REM Create temp directory
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM Check if FFmpeg already downloaded
set FFMPEG_EXE_PATH=%TEMP_DIR%\ffmpeg.exe

if exist "%FFMPEG_EXE_PATH%" (
    echo FFmpeg already downloaded.
) else (
    echo Downloading latest FFmpeg
    echo This may take a few minutes
    echo.
    
    powershell -Command "Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%TEMP_DIR%\%FFMPEG_ZIP%' -UseBasicParsing"
    
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to download FFmpeg!
        exit /b 1
    )
    
    echo Extracting FFmpeg...
    powershell -Command "Expand-Archive -Path '%TEMP_DIR%\%FFMPEG_ZIP%' -DestinationPath '%TEMP_DIR%' -Force"
    
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to extract FFmpeg!
        exit /b 1
    )
    
    REM Find the extracted folder
    for /d %%i in ("%TEMP_DIR%\ffmpeg-*") do set FFMPEG_DIR=%%i
    
    if defined FFMPEG_DIR (
        copy /y "%FFMPEG_DIR%\bin\ffmpeg.exe" "%FFMPEG_EXE_PATH%" >nul
        if %ERRORLEVEL% neq 0 (
            copy /y "%FFMPEG_DIR%\ffmpeg.exe" "%FFMPEG_EXE_PATH%" >nul
        )
    )
    
    if not exist "%FFMPEG_EXE_PATH%" (
        echo ERROR: Could not find ffmpeg.exe in extracted archive!
        exit /b 1
    )
    
    echo FFmpeg downloaded and extracted successfully!
)

echo.
echo Running flet build windows...
call flet build windows

if %ERRORLEVEL% neq 0 (
    echo Build failed!
    exit /b 1
)

echo.
echo Build completed successfully!
echo.

REM Find the build output folder (flet creates folder with version in name)
set BUILD_DIR=build\windows

if not defined BUILD_DIR (
    echo ERROR: Could not find build output folder
    echo Expected folder pattern: build\windows
    exit /b 1
)

echo Copying FFmpeg to build folder...
copy /y "%FFMPEG_EXE_PATH%" "%BUILD_DIR%\ffmpeg.exe"

if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to copy FFmpeg!
) else (
    echo FFmpeg copied successfully!
)

echo.
echo Renaming build folder...
set NEW_FOLDER_NAME=%APP_NAME%-v%APP_VERSION%
set RENAMED_FOLDER=%~dp0build\%NEW_FOLDER_NAME%

REM Remove existing folder if it exists
if exist "%RENAMED_FOLDER%" rmdir /s /q "%RENAMED_FOLDER%"

move "%BUILD_DIR%" "%RENAMED_FOLDER%" >nul
set BUILD_DIR=%RENAMED_FOLDER%

echo Folder renamed to: %NEW_FOLDER_NAME%

echo.
echo Creating ZIP file...
set ZIP_NAME=%NEW_FOLDER_NAME%.zip
powershell -Command "Compress-Archive -Path '%BUILD_DIR%\*' -DestinationPath '%~dp0build\%ZIP_NAME%' -Force"

if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to create ZIP file!
) else (
    echo ZIP file created: build\%ZIP_NAME%
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Output folder: build\%NEW_FOLDER_NAME%
echo ZIP file:      build\%ZIP_NAME%
echo.
echo Ready to distribute!
echo.

REM Cleanup temp files (optional - comment out to keep for future builds)
REM rmdir /s /q "%TEMP_DIR%"

pause
