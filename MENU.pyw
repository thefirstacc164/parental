"""
MENU.pyw - Parent Control Dashboard

Requires: relay_server.py running locally.

This is the styled dashboard version with persistent checkmark device selection:
  ☐ not selected
  ☑ selected

Click a device once to select it. Click the same device again to deselect it.
Selection is kept after actions and after Refresh Devices, as long as the device
still exists in the relay device list.
"""

from __future__ import annotations

import json
import threading
import time
import tkinter as tk
import tkinter.ttk as ttk
import urllib.error
import urllib.request
from tkinter import messagebox
from typing import Any

# === EDIT THIS TO MATCH relay_server.py and PC.pyw ===
RELAY_TOKEN = "thefirstaccievercreated164thefirstaccievercreated165thefirstaccievercreated166"
# =====================================================

DEFAULT_RELAY_URL = "https://parental-controll-url.onrender.com"
APP_TITLE = "Parent Control Dashboard"

# ── colour palette ────────────────────────────────────────────────────────────
BG = "#1e1e2e"
PANEL = "#2a2a3e"
ACCENT = "#0078d4"
ACCENT2 = "#e74c3c"
ACCENT3 = "#27ae60"
ACCENT_TROLL = "#f39c12"
TEXT = "#cdd6f4"
TEXT_DIM = "#6c7086"
TEXT_HEAD = "#ffffff"
BTN_H = 2
BTN_W = 18


# ─────────────────────────────────────────────────────────────────────────────
# Relay helper
# ─────────────────────────────────────────────────────────────────────────────
def relay_request(base_url: str, path: str, data: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    payload = dict(data)
    payload["token"] = RELAY_TOKEN
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection failed: {exc.reason}")


# ─────────────────────────────────────────────────────────────────────────────
# Styled widget helpers
# ─────────────────────────────────────────────────────────────────────────────
def styled_btn(
    parent: tk.Widget,
    text: str,
    cmd,
    color: str = ACCENT,
    width: int = BTN_W,
    height: int = BTN_H,
) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=cmd,
        bg=color,
        fg="white",
        activebackground=color,
        activeforeground="white",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        width=width,
        height=height,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
    )


def section_label(parent: tk.Widget, text: str) -> tk.Label:
    return tk.Label(
        parent,
        text=text,
        bg=PANEL,
        fg=TEXT_HEAD,
        font=("Segoe UI", 11, "bold"),
        anchor="w",
        padx=6,
    )


def dim_label(parent: tk.Widget, text: str) -> tk.Label:
    return tk.Label(
        parent,
        text=text,
        bg=PANEL,
        fg=TEXT_DIM,
        font=("Segoe UI", 8),
        anchor="w",
    )


def entry_row(parent: tk.Widget, label: str, default: str = "", width: int = 14) -> tk.StringVar:
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", padx=6, pady=2)
    tk.Label(
        row,
        text=label,
        bg=PANEL,
        fg=TEXT,
        font=("Segoe UI", 9),
        width=14,
        anchor="w",
    ).pack(side="left")
    var = tk.StringVar(value=default)
    tk.Entry(
        row,
        textvariable=var,
        width=width,
        bg="#13131f",
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        bd=4,
    ).pack(side="left", padx=4)
    return var


def spin_row(parent: tk.Widget, label: str, from_: int, to: int, default: int = 0, width: int = 7) -> tk.IntVar:
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", padx=6, pady=2)
    tk.Label(
        row,
        text=label,
        bg=PANEL,
        fg=TEXT,
        font=("Segoe UI", 9),
        width=14,
        anchor="w",
    ).pack(side="left")
    var = tk.IntVar(value=default)
    tk.Spinbox(
        row,
        from_=from_,
        to=to,
        textvariable=var,
        width=width,
        bg="#13131f",
        fg=TEXT,
        buttonbackground=PANEL,
        relief="flat",
        bd=4,
    ).pack(side="left", padx=4)
    return var


def separator(parent: tk.Widget) -> None:
    tk.Frame(parent, bg="#3a3a5e", height=1).pack(fill="x", padx=6, pady=6)


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x820")
        self.root.minsize(1100, 720)
        self.root.configure(bg=BG)

        self.relay_url = tk.StringVar(value=DEFAULT_RELAY_URL)
        self.status_var = tk.StringVar(value="Ready.")
        self.devices: list[dict[str, Any]] = []
        self.selected_device_id_value: str | None = None
        self.test_mode = tk.BooleanVar(value=False)

        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        top = tk.Frame(self.root, bg="#13131f", pady=6)
        top.pack(fill="x")

        tk.Label(
            top,
            text="🖥  Parent Control Dashboard",
            bg="#13131f",
            fg=TEXT_HEAD,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left", padx=14)

        tk.Checkbutton(
            top,
            text="🧪 Test Mode",
            variable=self.test_mode,
            bg="#13131f",
            fg=ACCENT_TROLL,
            selectcolor="#13131f",
            activebackground="#13131f",
            activeforeground=ACCENT_TROLL,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        ).pack(side="right", padx=14)

        relay_bar = tk.Frame(self.root, bg=PANEL, pady=6)
        relay_bar.pack(fill="x")

        tk.Label(relay_bar, text="Relay URL:", bg=PANEL, fg=TEXT, font=("Segoe UI", 9)).pack(side="left", padx=(10, 4))
        tk.Entry(
            relay_bar,
            textvariable=self.relay_url,
            width=48,
            bg="#13131f",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=4,
        ).pack(side="left")

        styled_btn(relay_bar, "⟳ Refresh Devices", self.refresh_devices, width=18, height=1).pack(side="left", padx=8)

        tk.Label(relay_bar, textvariable=self.status_var, bg=PANEL, fg=ACCENT, font=("Segoe UI", 9)).pack(side="left", padx=8)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        self._build_device_panel(left)
        self._build_output_panel(left)

        right = tk.Frame(body, bg=PANEL, width=420)
        right.pack(side="right", fill="both", padx=(10, 0))
        right.pack_propagate(False)

        self._build_action_panel(right)

    def _build_device_panel(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(
            parent,
            text=" Connected Devices ",
            bg=PANEL,
            fg=TEXT_HEAD,
            font=("Segoe UI", 10, "bold"),
            bd=1,
            relief="flat",
        )
        frame.pack(fill="both", expand=False, pady=(0, 8))

        self.device_list = tk.Listbox(
            frame,
            height=7,
            bg="#13131f",
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground="white",
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        sc = tk.Scrollbar(frame, orient="vertical", command=self.device_list.yview, bg=PANEL)
        self.device_list.configure(yscrollcommand=sc.set)
        self.device_list.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.device_list.bind("<ButtonRelease-1>", self.toggle_device_selection)
        sc.pack(side="right", fill="y")

    def _build_output_panel(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(
            parent,
            text=" Output ",
            bg=PANEL,
            fg=TEXT_HEAD,
            font=("Segoe UI", 10, "bold"),
            bd=1,
            relief="flat",
        )
        frame.pack(fill="both", expand=True)

        self.output_box = tk.Text(
            frame,
            bg="#13131f",
            fg=TEXT,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            wrap="word",
            state="disabled",
            highlightthickness=0,
        )
        sc = tk.Scrollbar(frame, orient="vertical", command=self.output_box.yview, bg=PANEL)
        self.output_box.configure(yscrollcommand=sc.set)
        self.output_box.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sc.pack(side="right", fill="y")

    def _build_action_panel(self, parent: tk.Widget) -> None:
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=PANEL, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#13131f",
            foreground=TEXT,
            padding=[10, 5],
            font=("Segoe UI", 9, "bold"),
        )
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "white")])

        self._build_tab_control(nb)
        self._build_tab_power(nb)
        self._build_tab_parental(nb)
        self._build_tab_troll(nb)

    # ── Tab: Control ────────────────────────────────────────────────────────
    def _build_tab_control(self, nb: ttk.Notebook) -> None:
        tab = tk.Frame(nb, bg=PANEL)
        nb.add(tab, text="📋 Control")

        section_label(tab, "Device Info").pack(fill="x", pady=(8, 2))
        f1 = tk.Frame(tab, bg=PANEL)
        f1.pack(fill="x", padx=6)
        styled_btn(f1, "Status", lambda: self.cmd("status"), ACCENT3).grid(row=0, column=0, padx=4, pady=4)
        styled_btn(f1, "Get Log", lambda: self.cmd("log", {"lines": 80}), ACCENT3).grid(row=0, column=1, padx=4, pady=4)

        separator(tab)
        section_label(tab, "Startup").pack(fill="x", pady=(0, 2))
        f2 = tk.Frame(tab, bg=PANEL)
        f2.pack(fill="x", padx=6)
        styled_btn(
            f2,
            "Add Startup",
            lambda: self.confirm_cmd("startup_add", "Add PC.pyw to Startup on the remote PC?"),
            ACCENT3,
        ).grid(row=0, column=0, padx=4, pady=4)
        styled_btn(
            f2,
            "Remove Startup",
            lambda: self.confirm_cmd("startup_remove", "Remove PC.pyw from Startup?"),
            ACCENT2,
        ).grid(row=0, column=1, padx=4, pady=4)

        separator(tab)
        section_label(tab, "Send Message").pack(fill="x", pady=(0, 2))
        self.msg_title = entry_row(tab, "Title:", "Message from parent", width=22)
        self.msg_body = entry_row(tab, "Message:", "Take a break!", width=22)
        styled_btn(tab, "📨 Send Message", self.send_message, ACCENT).pack(padx=10, pady=6, anchor="w")

        separator(tab)
        section_label(tab, "Lock").pack(fill="x", pady=(0, 2))
        styled_btn(tab, "🔒 Lock PC", lambda: self.confirm_cmd("lock", "Lock the remote PC now?"), ACCENT2).pack(
            padx=10, pady=4, anchor="w"
        )

        separator(tab)
        section_label(tab, "PC.pyw Client").pack(fill="x", pady=(0, 2))
        dim_label(tab, "Closes the visible PC.pyw client on the selected remote PC.").pack(anchor="w", padx=10)
        styled_btn(
            tab,
            "⛔ Stop PC.pyw Client",
            lambda: self.confirm_cmd("stop", "Close/stop PC.pyw on the selected remote PC?"),
            ACCENT2,
            width=22,
        ).pack(padx=10, pady=4, anchor="w")

        row_tray = tk.Frame(tab, bg=PANEL)
        row_tray.pack(fill="x", padx=10, pady=2, anchor="w")
        styled_btn(
            row_tray,
            "🙈 Hide Tray Icon",
            lambda: self.confirm_cmd("set_tray_visible", "Hide the tray icon on the selected PC?", args={"visible": False}),
            ACCENT2,
            width=16,
        ).pack(side="left", padx=3)
        styled_btn(
            row_tray,
            "👁 Show Tray Icon",
            lambda: self.confirm_cmd("set_tray_visible", "Show the tray icon on the selected PC?", args={"visible": True}),
            ACCENT3,
            width=16,
        ).pack(side="left", padx=3)

    # ── Tab: Power ──────────────────────────────────────────────────────────
    def _build_tab_power(self, nb: ttk.Notebook) -> None:
        tab = tk.Frame(nb, bg=PANEL)
        nb.add(tab, text="⚡ Power")

        section_label(tab, "Immediate Actions").pack(fill="x", pady=(8, 4))
        grid = tk.Frame(tab, bg=PANEL)
        grid.pack(fill="x", padx=6)

        actions = [
            ("💤 Sleep", "sleep", ACCENT),
            ("🌙 Hibernate", "hibernate", ACCENT),
            ("🔄 Restart", "restart", ACCENT_TROLL),
            ("⏹ Shutdown", "shutdown", ACCENT2),
            ("🚪 Log Off", "logoff", ACCENT2),
            ("❌ Cancel", "cancel_shutdown", ACCENT3),
        ]
        for i, (label, act, color) in enumerate(actions):
            r, c = divmod(i, 3)
            styled_btn(
                grid,
                label,
                lambda a=act: self.confirm_cmd(a, f"Send '{a}' to remote PC?"),
                color,
                width=15,
            ).grid(row=r, column=c, padx=4, pady=4)

        separator(tab)
        section_label(tab, "Timed / Scheduled").pack(fill="x", pady=(0, 4))
        dim_label(tab, "Delay (seconds) before shutdown/restart:").pack(anchor="w", padx=10)
        self.power_delay = spin_row(tab, "Delay (sec):", 0, 86400, 60)
        self.power_action2 = tk.StringVar(value="shutdown")

        row2 = tk.Frame(tab, bg=PANEL)
        row2.pack(fill="x", padx=6, pady=4)
        tk.Label(row2, text="Action:", bg=PANEL, fg=TEXT, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        ttk.Combobox(
            row2,
            textvariable=self.power_action2,
            values=["shutdown", "restart", "sleep", "hibernate", "logoff", "cancel_shutdown"],
            state="readonly",
            width=14,
        ).pack(side="left", padx=4)
        styled_btn(tab, "⏱ Schedule Action", self._schedule_power, ACCENT_TROLL).pack(padx=10, pady=6, anchor="w")

        separator(tab)
        section_label(tab, "Give Time (add seconds before pending)").pack(fill="x", pady=(0, 4))
        self.give_time_sec = spin_row(tab, "Extra secs:", 0, 86400, 300)

        row_gt = tk.Frame(tab, bg=PANEL)
        row_gt.pack(fill="x", padx=6, pady=4, anchor="w")
        styled_btn(
            row_gt,
            "⏳ Give More Time",
            self._give_time,
            ACCENT3,
            width=18,
        ).pack(side="left", padx=4)
        styled_btn(
            row_gt,
            "⛔ Cancel Shutdown",
            lambda: self.confirm_cmd("cancel_shutdown", "Cancel scheduled shutdown/restart?"),
            ACCENT2,
            width=18,
        ).pack(side="left", padx=4)

        separator(tab)
        dim_label(tab, "🧪 Test Mode: actions are sent with {'test': True}.").pack(anchor="w", padx=10, pady=4)

    def _schedule_power(self) -> None:
        act = self.power_action2.get()
        delay = 0 if act == "cancel_shutdown" else self.power_delay.get()
        self.confirm_cmd(act, f"Schedule '{act}' in {delay}s on remote PC?", args={"delay": delay})

    def _give_time(self) -> None:
        extra = self.give_time_sec.get()
        device_id = self.selected_device_id()
        if not device_id:
            return

        def _do() -> None:
            self._send_command_thread("cancel_shutdown", {}, device_id, refresh_after=False)
            time.sleep(0.5)
            self._send_command_thread("shutdown", {"delay": extra}, device_id)

        threading.Thread(target=_do, daemon=True).start()
        self.log(f"Give time: cancel + shutdown in {extra}s queued.")

    # ── Tab: Parental ────────────────────────────────────────────────────────
    def _build_tab_parental(self, nb: ttk.Notebook) -> None:
        tab = tk.Frame(nb, bg=PANEL)
        nb.add(tab, text="👁 Parental")

        section_label(tab, "Volume Control").pack(fill="x", pady=(8, 2))
        self.volume_level = spin_row(tab, "Volume %:", 0, 100, 50)
        styled_btn(tab, "🔊 Set Volume", lambda: self.cmd("set_volume", {"level": self.volume_level.get()}), ACCENT).pack(
            padx=10, pady=4, anchor="w"
        )

        separator(tab)
        section_label(tab, "Kill Process").pack(fill="x", pady=(0, 2))
        dim_label(tab, "e.g. chrome.exe, discord.exe, steam.exe").pack(anchor="w", padx=10)
        self.kill_proc = entry_row(tab, "Process:", "chrome.exe", width=20)
        styled_btn(
            tab,
            "💀 Kill Process",
            lambda: self.confirm_cmd(
                "kill_process",
                f"Kill '{self.kill_proc.get()}' on remote PC?",
                args={"process": self.kill_proc.get()},
            ),
            ACCENT2,
        ).pack(padx=10, pady=4, anchor="w")

        separator(tab)
        section_label(tab, "Open URL on Remote PC").pack(fill="x", pady=(0, 2))
        self.open_url_var = entry_row(tab, "URL:", "https://google.com", width=24)
        styled_btn(tab, "🌐 Open URL", lambda: self.cmd("open_url", {"url": self.open_url_var.get()}), ACCENT).pack(
            padx=10, pady=4, anchor="w"
        )

        separator(tab)
        section_label(tab, "Type Text on Remote PC").pack(fill="x", pady=(0, 2))
        dim_label(tab, "Text will be typed into whatever is focused.").pack(anchor="w", padx=10)
        self.type_text_var = entry_row(tab, "Text:", "Hello!", width=24)
        styled_btn(tab, "⌨ Type Text", lambda: self.cmd("type_text", {"text": self.type_text_var.get()}), ACCENT).pack(
            padx=10, pady=4, anchor="w"
        )

    # ── Tab: Troll ──────────────────────────────────────────────────────────
    def _build_tab_troll(self, nb: ttk.Notebook) -> None:
        tab = tk.Frame(nb, bg=PANEL)
        nb.add(tab, text="😈 Troll")

        tk.Label(
            tab,
            text="⚠ These commands only work if your relay_server.py and PC.pyw allow/implement them.",
            bg=PANEL,
            fg=ACCENT2,
            font=("Segoe UI", 8, "italic"),
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(6, 2))

        section_label(tab, "Blackout Screen").pack(fill="x", pady=(4, 2))
        self.blackout_sec = spin_row(tab, "Duration (s):", 1, 300, 10)
        styled_btn(
            tab,
            "🌑 Blackout Screen",
            lambda: self.confirm_cmd(
                "blackout",
                f"Black out screen for {self.blackout_sec.get()}s?",
                args={"seconds": self.blackout_sec.get()},
            ),
            "#2c2c54",
            width=20,
        ).pack(padx=10, pady=4, anchor="w")

        separator(tab)
        section_label(tab, "Spam Open Programs").pack(fill="x", pady=(0, 2))
        self.spam_prog = tk.StringVar(value="explorer")
        self.spam_count = spin_row(tab, "Count:", 1, 200, 20)
        row = tk.Frame(tab, bg=PANEL)
        row.pack(fill="x", padx=6, pady=2)
        tk.Label(row, text="Program:", bg=PANEL, fg=TEXT, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        ttk.Combobox(
            row,
            textvariable=self.spam_prog,
            values=["explorer", "notepad", "cmd", "calc", "mspaint", "taskmgr", "wordpad"],
            state="readonly",
            width=14,
        ).pack(side="left", padx=4)
        styled_btn(
            tab,
            "🚀 Spam Open",
            lambda: self.confirm_cmd(
                "spam_open",
                f"Open {self.spam_prog.get()} x{self.spam_count.get()} times?",
                args={"program": self.spam_prog.get(), "count": self.spam_count.get()},
            ),
            ACCENT_TROLL,
            width=20,
        ).pack(padx=10, pady=4, anchor="w")

        separator(tab)
        section_label(tab, "Flip Screen").pack(fill="x", pady=(0, 2))
        self.flip_dir = tk.StringVar(value="180")
        row2 = tk.Frame(tab, bg=PANEL)
        row2.pack(fill="x", padx=6, pady=2)
        tk.Label(row2, text="Direction:", bg=PANEL, fg=TEXT, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        ttk.Combobox(row2, textvariable=self.flip_dir, values=["0", "90", "180", "270"], state="readonly", width=8).pack(
            side="left", padx=4
        )
        styled_btn(
            tab,
            "🔄 Flip Screen",
            lambda: self.confirm_cmd(
                "flip_screen",
                f"Rotate screen {self.flip_dir.get()}°?",
                args={"direction": self.flip_dir.get()},
            ),
            "#8e44ad",
            width=20,
        ).pack(padx=10, pady=4, anchor="w")

        separator(tab)
        section_label(tab, "Volume Blast").pack(fill="x", pady=(0, 2))
        styled_btn(tab, "🔊 MAX Volume", lambda: self.confirm_cmd("set_volume", "Set volume to 100%?", args={"level": 100}), ACCENT2, width=20).pack(
            padx=10, pady=2, anchor="w"
        )
        styled_btn(tab, "🔇 Mute", lambda: self.confirm_cmd("set_volume", "Mute the remote PC?", args={"level": 0}), ACCENT, width=20).pack(
            padx=10, pady=2, anchor="w"
        )

        separator(tab)
        section_label(tab, "Quick Messages").pack(fill="x", pady=(0, 2))
        trolls = [
            ("⛔ Stop Gaming", "STOP", "Put the game down. NOW."),
            ("🍽 Dinner Time", "NOTICE", "Come eat dinner!"),
            ("😴 Bed Time", "NOTICE", "It's bed time. Turn off the PC."),
            ("👀 I See You", "WARNING", "I can see everything you are doing. 😉"),
        ]
        tgrid = tk.Frame(tab, bg=PANEL)
        tgrid.pack(fill="x", padx=6)
        for i, (label, title, body) in enumerate(trolls):
            r, c = divmod(i, 2)
            styled_btn(
                tgrid,
                label,
                lambda ti=title, b=body: self.cmd("message", {"title": ti, "message": b}),
                ACCENT_TROLL,
                width=18,
                height=1,
            ).grid(row=r, column=c, padx=3, pady=3)

    # ── Device selection / checkmarks ───────────────────────────────────────
    def selected_device_id(self) -> str | None:
        if not self.selected_device_id_value:
            messagebox.showerror(APP_TITLE, "Select a device first. Click a device to check it; click again to uncheck it.")
            return None
        return self.selected_device_id_value

    def toggle_device_selection(self, event=None) -> None:
        sel = self.device_list.curselection()
        if not sel:
            return

        index = sel[0]
        if index < 0 or index >= len(self.devices):
            return

        clicked_id = str(self.devices[index].get("device_id", ""))
        if not clicked_id:
            return

        if self.selected_device_id_value == clicked_id:
            self.selected_device_id_value = None
            self.set_status("Device deselected.")
        else:
            self.selected_device_id_value = clicked_id
            name = self.devices[index].get("computer", "device")
            self.set_status(f"Selected device: {name} ({clicked_id})")

        self.render_device_list()

    def render_device_list(self) -> None:
        self.device_list.delete(0, "end")
        for d in self.devices:
            device_id = str(d.get("device_id", ""))
            mark = "☑" if device_id == self.selected_device_id_value else "☐"
            online = "🟢 ONLINE" if d.get("online") else f"🔴 {d.get('seconds_since_seen')}s ago"
            startup = "✔ startup" if d.get("startup_installed") else "✘ startup"
            tray_state = "tray:ON" if d.get("tray_visible", True) else "tray:OFF"
            self.device_list.insert(
                "end",
                f"{mark} {d.get('computer')} / {d.get('user')}  {online}  {startup}  {tray_state}  [{device_id}]",
            )

    # ── Core command helpers ─────────────────────────────────────────────────
    def cmd(self, action: str, args: dict[str, Any] | None = None) -> None:
        device_id = self.selected_device_id()
        if not device_id:
            return

        if args is None:
            args = {}
        else:
            args = dict(args)

        if self.test_mode.get():
            args["test"] = True

        threading.Thread(target=self._send_command_thread, args=(action, args, device_id), daemon=True).start()

    def confirm_cmd(self, action: str, question: str, args: dict[str, Any] | None = None) -> None:
        if messagebox.askyesno(APP_TITLE, question):
            self.cmd(action, args or {})

    def _send_command_thread(
        self,
        action: str,
        args: dict[str, Any],
        device_id: str | None = None,
        refresh_after: bool = True,
    ) -> None:
        if device_id is None:
            return

        self.set_status(f"Sending '{action}'...")
        try:
            res = relay_request(
                self.relay_url.get(),
                "/menu/command",
                {"device_id": device_id, "action": action, "args": args},
            )
        except Exception as exc:
            self.set_status(str(exc))
            return

        cid = res.get("command_id", "")
        result = self._wait_result(cid)
        if result:
            pretty = json.dumps(result.get("result", result), indent=2)
            self.log(f"[{action}] {pretty}")
            self.set_status(f"✔ {action} done.")
        else:
            self.set_status(f"No result yet for '{action}'. Device may be offline.")

        if refresh_after:
            self.root.after(0, self.refresh_devices)

    def _wait_result(self, command_id: str, attempts: int = 15) -> dict[str, Any] | None:
        for _ in range(attempts):
            time.sleep(1)
            try:
                res = relay_request(self.relay_url.get(), "/menu/results", {"command_id": command_id})
                item = res.get("result")
                if item:
                    return item
            except Exception:
                pass
        return None

    def send_message(self) -> None:
        title = self.msg_title.get().strip()
        body = self.msg_body.get().strip()
        if not body:
            messagebox.showerror(APP_TITLE, "Message body is empty.")
            return
        self.cmd("message", {"title": title, "message": body})

    def refresh_devices(self) -> None:
        if RELAY_TOKEN.startswith("CHANGE-ME"):
            messagebox.showerror(APP_TITLE, "Edit RELAY_TOKEN first.")
            return

        try:
            result = relay_request(self.relay_url.get(), "/menu/devices", {})
        except Exception as exc:
            self.set_status(str(exc))
            return

        self.devices = result.get("devices", [])
        current_ids = {str(d.get("device_id", "")) for d in self.devices}

        # Keep the selected device only if the relay still knows it.
        if self.selected_device_id_value and self.selected_device_id_value not in current_ids:
            self.selected_device_id_value = None

        self.render_device_list()

        if self.selected_device_id_value:
            self.set_status(f"Found {len(self.devices)} device(s). Selection kept.")
        else:
            self.set_status(f"Found {len(self.devices)} device(s). Click a device to select it.")

    # ── Utility ──────────────────────────────────────────────────────────────
    def set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_var.set(text))
        self.log(text)

    def log(self, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")

        def _insert() -> None:
            self.output_box.configure(state="normal")
            self.output_box.insert("end", f"[{stamp}] {text}\n")
            self.output_box.see("end")
            self.output_box.configure(state="disabled")

        self.root.after(0, _insert)


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()