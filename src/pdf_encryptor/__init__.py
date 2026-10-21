"""PDF 加密工具入口。

用法：
  pdf-encryptor                  # 打开图形界面
  pdf-encryptor file.pdf         # 用本地默认密码（无则随机）加密
  pdf-encryptor file.pdf --password abc123
  pdf-encryptor file.pdf --random-password
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_default_password, save_default_password
from .core import encrypt_file, generate_password


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF 图片化 + 密码加密")
    parser.add_argument("pdf", nargs="?", help="要加密的 PDF 路径")
    parser.add_argument("--password", help="指定密码")
    parser.add_argument(
        "--random-password",
        action="store_true",
        help="强制使用随机密码（忽略默认密码）",
    )
    args = parser.parse_args()

    # 无参数 → GUI
    if not args.pdf:
        from .gui import run_gui

        run_gui()
        return

    if args.random_password:
        password = generate_password()
    elif args.password:
        password = args.password
    else:
        password = load_default_password() or generate_password()

    # 命令行指定的密码也记为默认，方便下次
    save_default_password(password)

    result = encrypt_file(Path(args.pdf), password=password)
    print("加密完成")
    print(f"文件: {result.pdf_path}")
    print(f"密码: {result.password}")
    print(f"密码文件: {result.password_path}")


if __name__ == "__main__":
    main()
