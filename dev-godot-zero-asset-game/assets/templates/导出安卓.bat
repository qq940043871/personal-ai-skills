@echo off
title 导出安卓 APK
rem ============================================================
rem  导出安卓 APK —— 需要先运行过一次 setup_android.ps1 装好工具链
rem ============================================================
setlocal EnableExtensions

set "TOOLCHAIN=%USERPROFILE%\godot-android"
set "JAVA_HOME=%TOOLCHAIN%\jdk"
set "ANDROID_HOME=%TOOLCHAIN%\android-sdk"
set "ANDROID_SDK_ROOT=%TOOLCHAIN%\android-sdk"

rem ---- 探测 Godot（命令行必须用 console 版 exe，否则无输出）----
set "GODOT="
where godot >nul 2>nul && set "GODOT=godot"
if not defined GODOT for /f "delims=" %%i in ('dir /b /s /o-n "C:\Program Files\Godot\Godot_v*_win64_console.exe" 2^>nul') do if not defined GODOT set "GODOT=%%i"
if not defined GODOT (
  echo [x] 未找到 Godot，请安装后重试，或编辑本脚本顶部手动指定 GODOT 变量。
  pause
  exit /b 1
)
echo [1/3] Godot: %GODOT%

if not exist "%TOOLCHAIN%\jdk\bin\java.exe" (
  echo [x] 未找到 JDK。请先运行 skill 的 setup_android.ps1 安装工具链。
  pause
  exit /b 1
)

if not exist "%~dp0export_presets.cfg" (
  echo [x] 缺少 export_presets.cfg（Android 导出预设）。
  pause
  exit /b 1
)

if not exist "%~dp0builds" mkdir "%~dp0builds"

echo [2/3] 刷新导入缓存...
"%GODOT%" --headless --path "%~dp0." --import >nul 2>nul

echo [3/3] 导出 release APK（debug 签名，可直接安装到手机）...
"%GODOT%" --headless --path "%~dp0." --export-release "Android"
if errorlevel 1 goto :fail

set "NEWAPK="
for /f "delims=" %%f in ('dir /b /o-d "%~dp0builds\*.apk" 2^>nul') do if not defined NEWAPK set "NEWAPK=%%f"
if not defined NEWAPK goto :fail

echo.
echo [ok] 导出成功，最新产物：
dir /o-d "%~dp0builds\*.apk" | findstr /i ".apk"
echo      传到手机安装即可（首次安装需允许「未知来源/安装未知应用」）。
pause
exit /b 0

:fail
echo.
echo [x] 导出失败。常见原因：导出模板未安装、签名/keystore 配置缺失、preset 名不是 Android。
echo      排查命令："%GODOT%" --headless --path "%~dp0." --export-release "Android"
pause
exit /b 1
