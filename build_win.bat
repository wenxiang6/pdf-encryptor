@echo off
REM 打包 Windows 版：生成单文件 exe（需在 Windows 上执行）
setlocal enabledelayedexpansion
chcp 65001 >nul

set APP_NAME=PDF加密工具

where uv >nul 2>nul
if errorlevel 1 (
  echo 错误：找不到 uv，请先安装 https://docs.astral.sh/uv/
  exit /b 1
)

echo ==^> 准备环境
uv sync --group dev
if errorlevel 1 exit /b 1

echo ==^> 清理旧产物
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

echo ==^> PyInstaller 打包 exe
uv run pyinstaller ^
  --noconfirm ^
  --windowed ^
  --onefile ^
  --name "%APP_NAME%" ^
  --collect-all pypdfium2 ^
  --collect-all cryptography ^
  --hidden-import PIL._tkinter_finder ^
  --paths src ^
  app_entry.py
if errorlevel 1 exit /b 1

if not exist "dist\%APP_NAME%.exe" (
  echo 错误：没有生成 dist\%APP_NAME%.exe
  exit /b 1
)

echo.
echo 完成：dist\%APP_NAME%.exe
echo 双击即可运行，无需安装 Python。
endlocal
