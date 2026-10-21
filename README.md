# PDF 加密工具

把 PDF **转成图片**（防止用工具改字体/内容），再用**随机密码**加密。  
加密结果放到桌面：

```text
桌面/加密后的pdf/
└── <原文件名>/
    ├── <原文件名>_加密.pdf   ← 需要密码才能打开
    └── password.txt          ← 随机密码
```

## 环境

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

```bash
uv sync
```

## 使用

### 图形界面

```bash
uv run pdf-encryptor
```

1. 「选择 PDF」
2. 密码框里是**本机记住的默认密码**（可直接改，会存到 `~/.pdf_encryptor/config.json`）
3. 点「随机密码」可一键换成随机密码
4. 「开始加密」

### 命令行

```bash
uv run pdf-encryptor /path/to/file.pdf                 # 用本地默认密码（无则随机）
uv run pdf-encryptor /path/to/file.pdf --password abc  # 指定密码
uv run pdf-encryptor /path/to/file.pdf --random-password
```

## 处理流程

1. 用 `pypdfium2` 把每一页 PDF 渲染成图片（默认 300 DPI，JPEG quality 95）
2. 用图片重新拼成 PDF（此时字体/文字已不可编辑）
3. 用 `pypdf`（PyPDF2 的维护续作）以 **AES-256** 加随机密码
4. 写入桌面目录，并生成 `password.txt`

> 说明：逻辑上是「先转图、再加密」。若先加密再转图，渲染时仍要解密，图片化防编辑的效果并不依赖第一层加密，因此这里做成一次转图 + 一次强加密。

## 打包（免安装）

### macOS（.app + .dmg）

在 Mac 上执行：

```bash
./build_mac.sh
```

产物：`dist/PDF加密工具.dmg`

### Windows（.exe）

> PyInstaller 不能交叉编译，Windows 的 exe **必须在 Windows 上打**（或走 CI）。

**方式 A：有 Windows 电脑**

```bat
build_win.bat
```

产物：`dist\PDF加密工具.exe`（单文件，双击即用）

**方式 B：GitHub Actions（不用装 Windows）**

推到 GitHub 后，手动触发 `build-windows-exe` workflow（或打 `v*` tag），  
在 Actions 产物里下载 `PDF加密工具-win-exe`。

## 依赖

| 库 | 用途 |
|---|---|
| pypdf | PDF 读写与 AES-256 加密（PyPDF2 后继） |
| pypdfium2 | PDF 渲染成图片，无需系统 poppler |
| Pillow | 拼装图片 PDF |
| cryptography | AES 加密后端 |
| pyinstaller | 打包（仅开发依赖） |
