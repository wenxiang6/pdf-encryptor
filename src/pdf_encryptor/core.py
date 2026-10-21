"""PDF 图片化 + 密码加密核心逻辑。

流程：
1. 将 PDF 每一页渲染成图片（栅格化，字体不可再编辑）
2. 用图片重新拼成 PDF
3. 用随机密码加密（pypdf，PyPDF2 的维护续作）
4. 输出到桌面「加密后的pdf/<原文件名>/」
"""

from __future__ import annotations

import os
import secrets
import string
import sys
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter

# 渲染 DPI：300 接近印刷清晰度；200 会明显发糊
RENDER_DPI = 300
# Pillow 写 PDF 时默认 JPEG quality≈75，文字会糊，这里拉高
JPEG_QUALITY = 95
PASSWORD_LENGTH = 16
OUTPUT_ROOT_NAME = "加密后的pdf"


@dataclass
class EncryptResult:
    pdf_path: Path
    password_path: Path
    password: str
    page_count: int


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """生成包含大小写字母和数字的随机密码。"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def desktop_dir() -> Path:
    """取桌面路径；兼容 Windows 与 OneDrive 重定向桌面。"""
    home = Path.home()
    candidates = [home / "Desktop"]

    if sys.platform == "win32":
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            candidates.append(Path(userprofile) / "Desktop")
        onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
        if onedrive:
            candidates.append(Path(onedrive) / "Desktop")
        # 兜底：读注册表里的 Desktop 实际路径
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            )
            try:
                desktop = winreg.QueryValueEx(key, "Desktop")[0]
                if desktop:
                    candidates.append(Path(os.path.expandvars(desktop)))
            finally:
                winreg.CloseKey(key)
        except Exception:
            pass

    for path in candidates:
        if path.is_dir():
            return path
    # 都不存在时退回标准桌面路径（ensure_output_root 会再创建）
    return home / "Desktop"


def ensure_output_root(base: Path | None = None) -> Path:
    """检查并创建桌面「加密后的pdf」目录。"""
    root = (base or desktop_dir()) / OUTPUT_ROOT_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def pdf_to_images(pdf_path: Path, dpi: int = RENDER_DPI) -> list[Image.Image]:
    """把 PDF 每一页渲染成 PIL 图片。"""
    doc = pdfium.PdfDocument(str(pdf_path))
    scale = dpi / 72
    images: list[Image.Image] = []
    try:
        for page in doc:
            # 线性插值 + 无子采样 JPEG，文字边缘更干净
            bitmap = page.render(scale=scale)
            images.append(bitmap.to_pil().convert("RGB"))
    finally:
        doc.close()
    return images


def images_to_pdf(
    images: list[Image.Image],
    out_path: Path,
    dpi: int = RENDER_DPI,
    quality: int = JPEG_QUALITY,
) -> None:
    """把图片列表拼成一个 PDF（高质量 JPEG 嵌入）。"""
    if not images:
        raise ValueError("没有可写入 PDF 的图片")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        out_path,
        "PDF",
        save_all=True,
        append_images=images[1:],
        resolution=dpi,
        quality=quality,
        optimize=True,
    )


def encrypt_pdf(src_path: Path, dst_path: Path, password: str) -> None:
    """用密码加密 PDF（AES-256）。"""
    reader = PdfReader(str(src_path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dst_path, "wb") as f:
        writer.write(f)


def encrypt_file(
    input_pdf: Path,
    output_base: Path | None = None,
    dpi: int = RENDER_DPI,
    password: str | None = None,
) -> EncryptResult:
    """
    完整流程：图片化 → 重拼 PDF → 密码加密 → 写到桌面输出目录。

    password 为空/None 时生成随机密码。

    输出结构:
      桌面/加密后的pdf/<文件名>/
        ├── <文件名>_加密.pdf
        └── password.txt
    """
    input_pdf = Path(input_pdf).expanduser().resolve()
    if not input_pdf.is_file():
        raise FileNotFoundError(f"找不到 PDF：{input_pdf}")
    if input_pdf.suffix.lower() != ".pdf":
        raise ValueError(f"只支持 PDF 文件：{input_pdf}")

    stem = input_pdf.stem
    root = ensure_output_root(output_base)
    out_dir = root / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    encrypted_pdf = out_dir / f"{stem}_加密.pdf"
    password_txt = out_dir / "password.txt"
    # 中间文件放输出目录，结束后删除
    flat_pdf = out_dir / f"{stem}_图片版.pdf"

    if password is None or password == "":
        password = generate_password()

    images = pdf_to_images(input_pdf, dpi=dpi)
    page_count = len(images)
    try:
        images_to_pdf(images, flat_pdf, dpi=dpi)
    finally:
        for img in images:
            img.close()

    try:
        encrypt_pdf(flat_pdf, encrypted_pdf, password)
    finally:
        if flat_pdf.exists():
            flat_pdf.unlink()

    password_txt.write_text(password + "\n", encoding="utf-8")

    return EncryptResult(
        pdf_path=encrypted_pdf,
        password_path=password_txt,
        password=password,
        page_count=page_count,
    )
