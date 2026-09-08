# admin_panel.py — Password-Protected Admin Panel
# Allows administrators to configure settings, whitelist domains, toggle protection, and change passwords.

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from config import (
    check_password, set_password, get_setting, set_setting,
    get_whitelist, add_to_whitelist, remove_from_whitelist
)
from hosts_manager import apply_blocks, get_block_status, is_admin


class AdminLoginDialog(tk.Toplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.on_success = on_success
        self.title("Admin Login — Adult Content Blocker")
        self.geometry("380x240")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")
        self.attributes("-topmost", True)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (380 // 2)
        y = (self.winfo_screenheight() // 2) - (240 // 2)
        self.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        lbl_title = tk.Label(
            self, text="🔒 Admin Authentication",
            font=("Segoe UI", 14, "bold"), bg="#1e1e2e", fg="#cdd6f4"
        )
        lbl_title.pack(pady=(20, 5))

        lbl_sub = tk.Label(
            self, text="Enter admin password to access settings.\nDefault password is: admin123",
            font=("Segoe UI", 9), bg="#1e1e2e", fg="#a6adc8", justify="center"
        )
        lbl_sub.pack(pady=(0, 15))

        # Password entry
        pwd_frame = tk.Frame(self, bg="#1e1e2e")
        pwd_frame.pack(pady=5)

        tk.Label(pwd_frame, text="Password:", font=("Segoe UI", 10), bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=5)
        self.entry_pwd = tk.Entry(pwd_frame, show="•", font=("Segoe UI", 11), width=20, bg="#313244", fg="#cdd6f4", insertbackground="white", relief="flat")
        self.entry_pwd.pack(side="left", padx=5)
        self.entry_pwd.focus()
        self.entry_pwd.bind("<Return>", lambda e: self._verify())

        # Buttons
        btn_frame = tk.Frame(self, bg="#1e1e2e")
        btn_frame.pack(pady=(20, 0))

        btn_login = tk.Button(
            btn_frame, text=" Login ", font=("Segoe UI", 10, "bold"),
            bg="#89b4fa", fg="#11111b", activebackground="#b4befe",
            relief="flat", padx=15, pady=4, cursor="hand2", command=self._verify
        )
        btn_login.pack(side="left", padx=10)

        btn_cancel = tk.Button(
            btn_frame, text=" Cancel ", font=("Segoe UI", 10),
            bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
            relief="flat", padx=15, pady=4, cursor="hand2", command=self.destroy
        )
        btn_cancel.pack(side="left", padx=10)

    def _verify(self):
        pwd = self.entry_pwd.get()
        if check_password(pwd):
            self.destroy()
            self.on_success()
        else:
            messagebox.showerror("Access Denied", "Incorrect password!", parent=self)
            self.entry_pwd.delete(0, tk.END)


class AdminPanel(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Control Panel — Adult Content Blocker")
        self.geometry("620x560")
        self.resizable(False, False)
        self.configure(bg="#181825")

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (620 // 2)
        y = (self.winfo_screenheight() // 2) - (560 // 2)
        self.geometry(f"+{x}+{y}")

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#11111b", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header, text="🛡 Adult Content Blocker — Settings",
            font=("Segoe UI", 14, "bold"), bg="#11111b", fg="#cdd6f4"
        )
        title.pack(side="left", padx=20, pady=15)

        # Main notebook (tabs)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#181825", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4", padding=[15, 8], font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", "#45475a")], foreground=[("selected", "#89b4fa")])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=15, pady=15)

        # Tab 1: General Settings
        tab_gen = tk.Frame(notebook, bg="#1e1e2e", padx=20, pady=20)
        notebook.add(tab_gen, text=" General Protection ")
        self._build_tab_general(tab_gen)

        # Tab 2: Whitelist
        tab_white = tk.Frame(notebook, bg="#1e1e2e", padx=20, pady=20)
        notebook.add(tab_white, text=" Whitelist ")
        self._build_tab_whitelist(tab_white)

        # Tab 3: Security & Password
        tab_sec = tk.Frame(notebook, bg="#1e1e2e", padx=20, pady=20)
        notebook.add(tab_sec, text=" Password & Security ")
        self._build_tab_security(tab_sec)

    def _build_tab_general(self, parent):
        # Protection status card
        card = tk.Frame(parent, bg="#313244", padx=15, pady=15)
        card.pack(fill="x", pady=(0, 15))

        self.lbl_status = tk.Label(
            card, text="Status: Loading...", font=("Segoe UI", 12, "bold"),
            bg="#313244", fg="#a6e3a1"
        )
        self.lbl_status.pack(anchor="w")

        status_info = get_block_status()
        admin_txt = "Yes (Full DNS + Keyword Protection)" if status_info["has_admin"] else "No (Keyword Protection only - Run as Admin for DNS protection)"
        self.lbl_admin = tk.Label(
            card, text=f"Administrator Rights: {admin_txt}",
            font=("Segoe UI", 9), bg="#313244", fg="#f38ba8" if not status_info["has_admin"] else "#a6e3a1"
        )
        self.lbl_admin.pack(anchor="w", pady=(5, 0))

        # ── Permanent lock notice ─────────────────────────────────────────
        lock_card = tk.Frame(parent, bg="#2a1a1a", padx=15, pady=12)
        lock_card.pack(fill="x", pady=(8, 12))

        tk.Label(
            lock_card,
            text="🔒  Protection is permanently locked ON",
            font=("Segoe UI", 11, "bold"), bg="#2a1a1a", fg="#f38ba8"
        ).pack(anchor="w")
        tk.Label(
            lock_card,
            text="The filtering layers below cannot be disabled for security reasons.",
            font=("Segoe UI", 9), bg="#2a1a1a", fg="#a6adc8"
        ).pack(anchor="w", pady=(4, 0))

        # ── Read-only layer status indicators ────────────────────────────
        def _status_row(parent, icon, text):
            row = tk.Frame(parent, bg="#1e1e2e")
            row.pack(anchor="w", pady=3)
            tk.Label(row, text=icon, font=("Segoe UI", 12),
                     bg="#1e1e2e", fg="#a6e3a1").pack(side="left")
            tk.Label(row, text=text, font=("Segoe UI", 10),
                     bg="#1e1e2e", fg="#a6adc8").pack(side="left", padx=(6, 0))

        _status_row(parent, "✅", "Hosts File DNS Blocking (3000+ domains) — Always Active")
        _status_row(parent, "✅", "Live Browser Tab Title Scanner (Keyword Detection) — Always Active")
        _status_row(parent, "✅", "Process Stealth Disguise (Blends as Windows System Service in Task Manager)")
        _status_row(parent, "✅", "Kernel DACL Anti-Kill Shield (Task Manager 'End Task' = Access Denied)")
        _status_row(parent, "✅", "Mutual Guardian Supervisor (Instant Auto-Revival Watchdog) — Active")
        _status_row(parent, "✅", "Permanent Background Protection (No exit option in tray menu) — Active")

        # ── Apply / Refresh DNS button ────────────────────────────────────
        btn_apply = tk.Button(
            parent, text=" Re-Apply Hosts File DNS Blocking ",
            font=("Segoe UI", 10, "bold"), bg="#a6e3a1", fg="#11111b",
            activebackground="#94e2d5", relief="flat", padx=15, pady=8,
            cursor="hand2", command=self._apply_hosts_blocking
        )
        btn_apply.pack(anchor="w", pady=(15, 5))

    def _build_tab_whitelist(self, parent):
        tk.Label(
            parent, text="Whitelisted Domains (Will NOT be blocked):",
            font=("Segoe UI", 10, "bold"), bg="#1e1e2e", fg="#cdd6f4"
        ).pack(anchor="w", pady=(0, 5))

        # Add domain box
        add_frame = tk.Frame(parent, bg="#1e1e2e")
        add_frame.pack(fill="x", pady=5)

        self.entry_domain = tk.Entry(
            add_frame, font=("Segoe UI", 10), bg="#313244", fg="#cdd6f4",
            insertbackground="white", relief="flat", width=30
        )
        self.entry_domain.pack(side="left", padx=(0, 10))
        self.entry_domain.bind("<Return>", lambda e: self._add_whitelist())

        btn_add = tk.Button(
            add_frame, text=" Add Domain ", font=("Segoe UI", 9, "bold"),
            bg="#89b4fa", fg="#11111b", relief="flat", padx=10, pady=2,
            cursor="hand2", command=self._add_whitelist
        )
        btn_add.pack(side="left")

        # Whitelist Listbox
        list_frame = tk.Frame(parent, bg="#1e1e2e")
        list_frame.pack(fill="both", expand=True, pady=10)

        self.lb_whitelist = tk.Listbox(
            list_frame, font=("Consolas", 10), bg="#313244", fg="#cdd6f4",
            selectbackground="#45475a", selectforeground="#89b4fa", relief="flat"
        )
        self.lb_whitelist.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, command=self.lb_whitelist.yview)
        scrollbar.pack(side="right", fill="y")
        self.lb_whitelist.config(yscrollcommand=scrollbar.set)

        btn_del = tk.Button(
            parent, text=" Remove Selected ", font=("Segoe UI", 9),
            bg="#f38ba8", fg="#11111b", relief="flat", padx=10, pady=4,
            cursor="hand2", command=self._del_whitelist
        )
        btn_del.pack(anchor="w", pady=5)

    def _build_tab_security(self, parent):
        tk.Label(
            parent, text="Change Admin Password",
            font=("Segoe UI", 11, "bold"), bg="#1e1e2e", fg="#cdd6f4"
        ).pack(anchor="w", pady=(0, 15))

        f1 = tk.Frame(parent, bg="#1e1e2e")
        f1.pack(anchor="w", pady=5)
        tk.Label(f1, text="Current Password:", font=("Segoe UI", 10), bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w").pack(side="left")
        self.entry_curr_pwd = tk.Entry(f1, show="•", font=("Segoe UI", 10), bg="#313244", fg="#cdd6f4", insertbackground="white", relief="flat", width=20)
        self.entry_curr_pwd.pack(side="left")

        f2 = tk.Frame(parent, bg="#1e1e2e")
        f2.pack(anchor="w", pady=5)
        tk.Label(f2, text="New Password:", font=("Segoe UI", 10), bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w").pack(side="left")
        self.entry_new_pwd = tk.Entry(f2, show="•", font=("Segoe UI", 10), bg="#313244", fg="#cdd6f4", insertbackground="white", relief="flat", width=20)
        self.entry_new_pwd.pack(side="left")

        f3 = tk.Frame(parent, bg="#1e1e2e")
        f3.pack(anchor="w", pady=5)
        tk.Label(f3, text="Confirm Password:", font=("Segoe UI", 10), bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w").pack(side="left")
        self.entry_confirm_pwd = tk.Entry(f3, show="•", font=("Segoe UI", 10), bg="#313244", fg="#cdd6f4", insertbackground="white", relief="flat", width=20)
        self.entry_confirm_pwd.pack(side="left")

        btn_chg_pwd = tk.Button(
            parent, text=" Update Password ", font=("Segoe UI", 10, "bold"),
            bg="#89b4fa", fg="#11111b", relief="flat", padx=15, pady=6,
            cursor="hand2", command=self._update_password
        )
        btn_chg_pwd.pack(anchor="w", pady=(15, 0))

    def _load_settings(self):
        status_info = get_block_status()
        if get_setting("enabled"):
            self.lbl_status.config(text="Status: Active 🟢", fg="#a6e3a1")
        else:
            self.lbl_status.config(text="Status: Disabled 🔴", fg="#f38ba8")

        self._refresh_whitelist()

    def _refresh_whitelist(self):
        self.lb_whitelist.delete(0, tk.END)
        for domain in get_whitelist():
            self.lb_whitelist.insert(tk.END, domain)


    def _save_options(self):
        # Protection layers are permanently locked ON — settings cannot be changed.
        # Force values back to True in case something external wrote to config.
        set_setting("block_hosts", True)
        set_setting("monitor_titles", True)
        set_setting("randomize_password", True)

    def _apply_hosts_blocking(self):
        if not is_admin():
            messagebox.showwarning(
                "Admin Privileges Required",
                "To modify the hosts file, please restart this application as Administrator.",
                parent=self
            )
            return
        success, count = apply_blocks()
        if success:
            messagebox.showinfo("Success", f"Successfully applied hosts blocking for {count} adult domains!", parent=self)
        else:
            messagebox.showerror("Error", "Failed to update hosts file.", parent=self)

    def _add_whitelist(self):
        domain = self.entry_domain.get().strip()
        if domain:
            add_to_whitelist(domain)
            self.entry_domain.delete(0, tk.END)
            self._refresh_whitelist()
            if is_admin() and get_setting("block_hosts"):
                apply_blocks()

    def _del_whitelist(self):
        sel = self.lb_whitelist.curselection()
        if sel:
            domain = self.lb_whitelist.get(sel[0])
            remove_from_whitelist(domain)
            self._refresh_whitelist()
            if is_admin() and get_setting("block_hosts"):
                apply_blocks()

    def _update_password(self):
        curr = self.entry_curr_pwd.get()
        new = self.entry_new_pwd.get()
        confirm = self.entry_confirm_pwd.get()

        if not check_password(curr):
            messagebox.showerror("Error", "Current password is incorrect!", parent=self)
            return
        if not new:
            messagebox.showerror("Error", "New password cannot be empty!", parent=self)
            return
        if new != confirm:
            messagebox.showerror("Error", "New passwords do not match!", parent=self)
            return

        set_password(new)
        messagebox.showinfo("Success", "Password updated successfully!", parent=self)
        self.entry_curr_pwd.delete(0, tk.END)


def open_admin_panel(parent=None):
    def launch():
        panel = AdminPanel(parent)
        panel.focus_force()

    login = AdminLoginDialog(parent, launch)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_admin_panel(root)
    root.mainloop()
