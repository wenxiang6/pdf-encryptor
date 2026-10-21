#!/usr/bin/env bash
# 打包 macOS 版：生成 .app，再做成 .dmg
set -euo pipefail

APP_NAME="PDF加密工具"
DIST=dist
BUILD=build

echo "==> 清理旧产物"
rm -rf "$DIST" "$BUILD" *.spec

echo "==> PyInstaller 打包 .app"
uv run pyinstaller \
  --noconfirm \
  --windowed \
  --name "$APP_NAME" \
  --collect-all pypdfium2 \
  --collect-all cryptography \
  --hidden-import PIL._tkinter_finder \
  --paths src \
  app_entry.py

APP_PATH="$DIST/$APP_NAME.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "错误：没有生成 $APP_PATH" >&2
  exit 1
fi

echo "==> 生成 DMG"
DMG_PATH="$DIST/$APP_NAME.dmg"
rm -f "$DMG_PATH"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$APP_PATH" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "完成：$DMG_PATH"
