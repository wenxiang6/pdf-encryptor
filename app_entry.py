"""PyInstaller 打包入口（避免包内相对导入问题）。"""

from pdf_encryptor import main

if __name__ == "__main__":
    main()
