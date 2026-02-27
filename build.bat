@echo off
REM Build script for YouTube Downloader with Automatic FFmpeg Download
REM
REM This script will:
REM   1. Download the latest FFmpeg from GitHub (if not already present)
REM   2. Build the Windows app using flet
REM   3. Copy FFmpeg to the build output folder

setlocal enabledelayedexpansion

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

    echo Extracting FFmpeg
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

REM Find the build output folder
set BUILD_DIR=build\windows

if not defined BUILD_DIR (
    echo ERROR: Could not find build output folder
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
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Output folder: %BUILD_DIR%
echo.
echo IMPORTANT: Copy the entire folder to distribute.
echo The app requires ffmpeg.exe in the same folder as youtube-downloader.exe
echo.

REM Cleanup temp files (optional - comment out to keep for future builds)
REM rmdir /s /q "%TEMP_DIR%"

pause
