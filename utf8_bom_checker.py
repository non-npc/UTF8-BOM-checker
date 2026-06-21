#!/usr/bin/env python3
"""
UTF-8 BOM Checker

Checks single files or recursively scans folders for Stellaris localisation files
that are missing UTF-8 BOM. Can apply BOM fixes in bulk with optional backups.
"""

from __future__ import annotations

import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


UTF8_BOM = b"\xef\xbb\xbf"
LOCALISATION_EXTENSIONS = {".yml"}


class Utf8BomChecker(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("UTF-8 BOM Checker")
        self.geometry("920x600")
        self.minsize(820, 520)

        self.selected_file: Path | None = None
        self.selected_folder: Path | None = None
        self.results: list[tuple[Path, str]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        main = tk.Frame(self, padx=14, pady=14)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            main,
            text="UTF-8 BOM Checker",
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        tk.Label(
            main,
            text="Check one file or recursively scan a folder for .yml localisation files.",
            anchor="w",
        ).pack(fill=tk.X, pady=(4, 12))

        # File selection
        file_box = tk.LabelFrame(main, text="Check Single File", padx=10, pady=8)
        file_box.pack(fill=tk.X, pady=(0, 8))

        self.file_var = tk.StringVar(value="No file selected")
        tk.Entry(file_box, textvariable=self.file_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        tk.Button(file_box, text="Select File", command=self.select_file).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # Folder selection
        folder_box = tk.LabelFrame(main, text="Scan Folder", padx=10, pady=8)
        folder_box.pack(fill=tk.X, pady=(0, 8))

        self.folder_var = tk.StringVar(value="No folder selected")
        tk.Entry(folder_box, textvariable=self.folder_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        tk.Button(folder_box, text="Select Folder", command=self.select_folder).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        options = tk.Frame(main)
        options.pack(fill=tk.X, pady=(2, 8))

        self.recursive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options, text="Scan subfolders", variable=self.recursive_var).pack(side=tk.LEFT)

        self.backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options,
            text="Create .bak backup before modifying",
            variable=self.backup_var,
        ).pack(side=tk.LEFT, padx=(20, 0))

        tk.Button(options, text="Check Selected File", command=self.check_selected_file).pack(
            side=tk.RIGHT
        )
        tk.Button(options, text="Scan Selected Folder", command=self.scan_selected_folder).pack(
            side=tk.RIGHT, padx=(0, 8)
        )

        result_box = tk.LabelFrame(main, text="Results", padx=8, pady=8)
        result_box.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            result_box,
            columns=("status", "file"),
            show="headings",
            selectmode="extended",
        )
        self.tree.heading("status", text="Status")
        self.tree.heading("file", text="File")
        self.tree.column("status", width=140, stretch=False)
        self.tree.column("file", width=720, stretch=True)

        yscroll = ttk.Scrollbar(result_box, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = tk.Frame(main)
        bottom.pack(fill=tk.X, pady=(10, 0))

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(bottom, textvariable=self.status_var, anchor="w").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        self.fix_btn = tk.Button(
            bottom,
            text="Apply BOM to Missing Files",
            command=self.apply_bom_to_missing,
            state=tk.DISABLED,
        )
        self.fix_btn.pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(bottom, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def select_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select file",
            filetypes=[
                ("Localisation files", "*.yml"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self.selected_file = Path(filename)
            self.file_var.set(str(self.selected_file))
            self.check_selected_file()

    def select_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder to scan")
        if folder:
            self.selected_folder = Path(folder)
            self.folder_var.set(str(self.selected_folder))
            self.scan_selected_folder()

    def check_selected_file(self) -> None:
        if not self.selected_file:
            messagebox.showwarning("No file selected", "Please select a file first.")
            return

        self._check_files([self.selected_file])

    def scan_selected_folder(self) -> None:
        if not self.selected_folder:
            messagebox.showwarning("No folder selected", "Please select a folder first.")
            return

        if self.recursive_var.get():
            files = [
                p for p in self.selected_folder.rglob("*")
                if p.is_file() and p.suffix.lower() in LOCALISATION_EXTENSIONS
            ]
        else:
            files = [
                p for p in self.selected_folder.iterdir()
                if p.is_file() and p.suffix.lower() in LOCALISATION_EXTENSIONS
            ]

        files.sort(key=lambda p: str(p).lower())
        self._check_files(files)

    def _check_files(self, files: list[Path]) -> None:
        self.results.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not files:
            self.status_var.set("No .yml files found.")
            self.fix_btn.config(state=tk.DISABLED)
            return

        has_bom = 0
        missing_bom = 0
        errors = 0

        for path in files:
            status = self._check_status(path)
            self.results.append((path, status))
            self.tree.insert("", tk.END, values=(status, str(path)))

            if status == "Has BOM":
                has_bom += 1
            elif status == "Missing BOM":
                missing_bom += 1
            else:
                errors += 1

        self.status_var.set(
            f"Checked {len(files)} file(s). Has BOM: {has_bom}. Missing BOM: {missing_bom}. Errors: {errors}."
        )
        self.fix_btn.config(state=tk.NORMAL if missing_bom else tk.DISABLED)

    @staticmethod
    def _check_status(path: Path) -> str:
        try:
            with path.open("rb") as f:
                return "Has BOM" if f.read(3) == UTF8_BOM else "Missing BOM"
        except OSError:
            return "Read Error"

    def apply_bom_to_missing(self) -> None:
        missing = [p for p, status in self.results if status == "Missing BOM"]

        if not missing:
            messagebox.showinfo("Nothing to fix", "No files are missing UTF-8 BOM.")
            return

        if not messagebox.askyesno(
            "Apply UTF-8 BOM",
            f"Add UTF-8 BOM to {len(missing)} missing file(s)?",
        ):
            return

        fixed = 0
        failed: list[str] = []

        for path in missing:
            try:
                data = path.read_bytes()
                if data.startswith(UTF8_BOM):
                    continue

                if self.backup_var.get():
                    shutil.copy2(path, self._backup_path(path))

                path.write_bytes(UTF8_BOM + data)
                fixed += 1
            except OSError as exc:
                failed.append(f"{path}: {exc}")

        # Refresh current view.
        if self.selected_folder:
            self.scan_selected_folder()
        elif self.selected_file:
            self.check_selected_file()

        if failed:
            messagebox.showwarning(
                "Finished with errors",
                f"Fixed {fixed} file(s). Failed: {len(failed)}.\n\n" + "\n".join(failed[:8]),
            )
        else:
            messagebox.showinfo("Done", f"Fixed {fixed} file(s).")

    @staticmethod
    def _backup_path(path: Path) -> Path:
        candidate = path.with_name(path.name + ".bak")
        if not candidate.exists():
            return candidate

        index = 1
        while True:
            candidate = path.with_name(f"{path.name}.bak{index}")
            if not candidate.exists():
                return candidate
            index += 1


if __name__ == "__main__":
    Utf8BomChecker().mainloop()
