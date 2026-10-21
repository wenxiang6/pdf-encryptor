"""简易图形界面：选 PDF → 加密 → 写到桌面。

注意：后台线程不能直接碰 Tkinter。工作线程只往 queue 里塞结果，
由主线程的 after 轮询取出后更新界面。
"""

from __future__ import annotations

import queue
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from .config import load_default_password, save_default_password
from .core import EncryptResult, encrypt_file, generate_password


@dataclass
class _Ok:
    result: EncryptResult


@dataclass
class _Err:
    short: str
    detail: str


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF 加密工具")
        self.minsize(520, 300)
        self.geometry("560x320")

        self.selected_path: Path | None = None
        self._busy = False
        self._results: queue.Queue[_Ok | _Err] = queue.Queue()

        self._build_ui()
        self.after(100, self._poll_results)

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 8}

        title = ttk.Label(self, text="PDF 图片化 + 密码加密", font=("Helvetica", 16, "bold"))
        title.pack(anchor="w", **pad)

        hint = ttk.Label(
            self,
            text="转换成图片防止编辑字体，再用密码加密\n输出到：桌面/加密后的pdf/<文件名>/",
            foreground="#555555",
        )
        hint.pack(anchor="w", **pad)

        # 文件行
        file_row = ttk.Frame(self)
        file_row.pack(fill="x", **pad)

        self.path_var = tk.StringVar(value="尚未选择文件")
        path_label = ttk.Label(file_row, textvariable=self.path_var, width=42)
        path_label.pack(side="left", fill="x", expand=True)

        self.choose_btn = ttk.Button(file_row, text="选择 PDF", command=self.choose_file)
        self.choose_btn.pack(side="left", padx=(8, 0))

        # 密码行
        pw_row = ttk.Frame(self)
        pw_row.pack(fill="x", **pad)

        ttk.Label(pw_row, text="密　码").pack(side="left")

        self.password_var = tk.StringVar(value=load_default_password())
        self.password_entry = ttk.Entry(pw_row, textvariable=self.password_var, width=28)
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.password_var.trace_add("write", self._on_password_changed)

        self.random_btn = ttk.Button(pw_row, text="随机密码", command=self.use_random_password)
        self.random_btn.pack(side="left")

        pw_hint = ttk.Label(
            self,
            text="密码会记住到本机（~/.pdf_encryptor/config.json），可直接修改",
            foreground="#888888",
        )
        pw_hint.pack(anchor="w", padx=16)

        # 按钮 / 进度
        self.encrypt_btn = ttk.Button(self, text="开始加密", command=self.start_encrypt)
        self.encrypt_btn.pack(anchor="e", **pad)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=16, pady=(4, 8))

        self.status_var = tk.StringVar(value="就绪")
        status = ttk.Label(self, textvariable=self.status_var, foreground="#333333")
        status.pack(anchor="w", padx=16, pady=(0, 12))

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.selected_path = Path(path)
        self.path_var.set(self.selected_path.name)
        self.status_var.set(f"已选择：{self.selected_path}")

    def use_random_password(self) -> None:
        self.password_var.set(generate_password())
        self.status_var.set("已生成随机密码")

    def _on_password_changed(self, *_args) -> None:
        # 修改后立即持久化，下次打开仍是这个默认密码
        if self._busy:
            return
        try:
            save_default_password(self.password_var.get())
        except OSError:
            pass

    def current_password(self) -> str:
        return self.password_var.get().strip()

    def start_encrypt(self) -> None:
        if self._busy:
            return
        if not self.selected_path:
            messagebox.showwarning("提示", "请先选择一个 PDF 文件")
            return

        password = self.current_password()
        if not password:
            messagebox.showwarning("提示", "密码不能为空\n可点「随机密码」生成一个")
            return

        # 加密前再存一次，确保和界面一致
        try:
            save_default_password(password)
        except OSError:
            pass

        self._busy = True
        self.encrypt_btn.configure(state="disabled")
        self.choose_btn.configure(state="disabled")
        self.random_btn.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set("正在处理，请稍候…")

        path = self.selected_path
        threading.Thread(target=self._run, args=(path, password), daemon=True).start()

    def _run(self, path: Path, password: str) -> None:
        """工作线程：只负责干活和往队列塞消息，不碰 UI。"""
        try:
            result = encrypt_file(path, password=password)
        except Exception as exc:  # noqa: BLE001 — GUI 需要展示任何错误
            self._results.put(_Err(str(exc), f"{exc}\n\n{traceback.format_exc()}"))
            return
        self._results.put(_Ok(result))

    def _poll_results(self) -> None:
        """主线程定时取结果并刷新界面。"""
        try:
            while True:
                msg = self._results.get_nowait()
                self._apply_result(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_results)

    def _apply_result(self, msg: _Ok | _Err) -> None:
        self._busy = False
        self.progress.stop()
        self.encrypt_btn.configure(state="normal")
        self.choose_btn.configure(state="normal")
        self.random_btn.configure(state="normal")

        if isinstance(msg, _Ok):
            result = msg.result
            self.status_var.set(f"完成：{result.pdf_path}")
            messagebox.showinfo(
                "加密完成",
                f"共 {result.page_count} 页\n\n"
                f"加密文件：\n{result.pdf_path}\n\n"
                f"密码文件：\n{result.password_path}\n\n"
                f"密码：{result.password}",
            )
        else:
            self.status_var.set(f"失败：{msg.short}")
            messagebox.showerror("出错了", msg.detail)


def run_gui() -> None:
    app = App()
    app.mainloop()
