"""Simple single-folder desktop AI chatbot (OpenAI + Google Gemini).

Requirements:
- Python 3.10+
- No third-party dependencies

Run:
    python app.py
"""

from __future__ import annotations

import json
import math
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from urllib import error, request
from urllib.request import ProxyHandler, build_opener

# ── colour palette ────────────────────────────────────────────────────────────
_BG       = "#0d1117"   # root / window
_PANEL    = "#0d1a2e"   # sidebar glass
_CARD     = "#0f1828"   # header / card glass
_INPUT    = "#111e30"   # entry / textbox
_INPUT_HV = "#172440"   # entry hover
_BTN      = "#1a2e4a"   # default button
_BTN_HV   = "#1d4ed8"   # button hover (deep blue)
_ACCENT   = "#3b82f6"   # primary accent – electric blue
_ACCENT_H = "#22d3ee"   # accent hover – cyan
_DIVIDER  = "#172235"   # separator
_FG       = "#e2e8f0"   # primary text
_FG2      = "#6b90b8"   # secondary text
_FG3      = "#2e4460"   # muted / hint text
_USER     = "#22d3ee"   # user name label – cyan
_ASST     = "#818cf8"   # assistant label – indigo/violet
_ERR      = "#f87171"   # error
_GBORDER  = "#1f3050"   # glass card border
# ────────────────────────────────────────────────────────────────────────────


class ChatbotApp:
    _SPIN = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    class _RoundBtn(tk.Canvas):
        """Canvas button with genuine rounded corners, hover animation, and glow ring."""
        _R = 10

        def __init__(self, parent, *, text, command,
                     bg, fg, hover_bg, hover_fg=_FG,
                     padx=12, pady=6, font=("Segoe UI", 9)):
            self._cmd      = command
            self._n_bg     = bg
            self._n_fg     = fg
            self._h_bg     = hover_bg
            self._h_fg     = hover_fg
            self._curfont  = font
            self._disabled = False
            self._aj       = [None]
            self._gj       = [None]

            f  = tkfont.Font(font=font)
            tw = f.measure(text)
            th = f.metrics("linespace")
            w, h = tw + padx * 2, th + pady * 2

            super().__init__(parent, width=w + 6, height=h + 6,
                             bd=0, highlightthickness=0,
                             bg=parent.cget("bg"))
            # Glow halo ring (3px outside the button, starts transparent)
            self._idglow = self._rrect(0, 0, w + 6, h + 6, self._R + 3,
                                       fill=parent.cget("bg"), outline="")
            self._idbg   = self._rrect(3, 3, w + 3, h + 3, self._R, fill=bg)
            self._idtxt  = self.create_text((w + 6) // 2, (h + 6) // 2,
                                             text=text, fill=fg, font=font)

            self.bind("<Enter>",           self._on_enter)
            self.bind("<Leave>",           self._on_leave)
            self.bind("<ButtonPress-1>",   self._on_press)
            self.bind("<ButtonRelease-1>", self._on_release)
            super().configure(cursor="hand2")

        def _rrect(self, x1, y1, x2, y2, r, **kw):
            pts = [x1+r, y1,  x2-r, y1,  x2,   y1,  x2,   y1+r,
                   x2,   y2-r, x2,  y2,  x2-r, y2,  x1+r, y2,
                   x1,   y2,  x1,   y2-r, x1,  y1+r, x1,  y1]
            return self.create_polygon(pts, smooth=True, **kw)

        @staticmethod
        def _lp(a, b, t):
            r  = round(int(a[1:3], 16) * (1-t) + int(b[1:3], 16) * t)
            g  = round(int(a[3:5], 16) * (1-t) + int(b[3:5], 16) * t)
            bv = round(int(a[5:7], 16) * (1-t) + int(b[5:7], 16) * t)
            return f"#{r:02x}{g:02x}{bv:02x}"

        def _anim(self, tb, tf, step=0):
            if self._aj[0]:
                try: self.after_cancel(self._aj[0])
                except Exception: pass
            if step > 9 or self._disabled:
                return
            try:
                self.itemconfigure(self._idbg,  fill=self._lp(self.itemcget(self._idbg,  "fill"), tb, 0.38))
                self.itemconfigure(self._idtxt, fill=self._lp(self.itemcget(self._idtxt, "fill"), tf, 0.38))
            except tk.TclError:
                return
            self._aj[0] = self.after(11, lambda: self._anim(tb, tf, step + 1))

        def _glow_anim(self, target, step=0):
            """Pulse the glow halo toward target colour."""
            if self._gj[0]:
                try: self.after_cancel(self._gj[0])
                except Exception: pass
            if step > 8 or self._disabled:
                return
            try:
                cur = self.itemcget(self._idglow, "fill")
                self.itemconfigure(self._idglow, fill=self._lp(cur, target, 0.4))
            except tk.TclError:
                return
            self._gj[0] = self.after(14, lambda: self._glow_anim(target, step + 1))

        def _on_enter(self, _):
            if not self._disabled:
                self._anim(self._h_bg, self._h_fg)
                self._glow_anim(self._lp(self._h_bg, "#000000", 0.35))
        def _on_leave(self, _):
            if not self._disabled:
                self._anim(self._n_bg, self._n_fg)
                self._glow_anim(super().cget("bg"))
        def _on_press(self, _):
            if not self._disabled:
                self.itemconfigure(self._idbg, fill=self._lp(self._h_bg, "#000000", 0.18))
        def _on_release(self, _):
            if not self._disabled:
                self.itemconfigure(self._idbg, fill=self._h_bg)
                if self._cmd: self._cmd()

        def configure(self, **kw):
            if "state" in kw:
                s = kw.pop("state")
                self._disabled = (s == "disabled")
                dim = _FG3
                self.itemconfigure(self._idbg,  fill=dim if self._disabled else self._n_bg)
                self.itemconfigure(self._idtxt, fill=dim if self._disabled else self._n_fg)
                super().configure(cursor="" if self._disabled else "hand2")
            if "bg" in kw:
                nb = kw.pop("bg")
                self._n_bg = nb
                if not self._disabled:
                    self.itemconfigure(self._idbg, fill=nb)
            if "font" in kw:
                self._curfont = kw.pop("font")
                self.itemconfigure(self._idtxt, font=self._curfont)
            kw.pop("padx", None); kw.pop("pady", None)
            if kw: super().configure(**kw)

        def cget(self, key):
            if key == "bg": return self.itemcget(self._idbg, "fill")
            return super().cget(key)

    class _RoundFrame(tk.Canvas):
        """Canvas that draws a rounded-rect background; add content to .inner."""

        def __init__(self, parent, fill: str, radius: int = 18,
                     padx: int = 14, pady: int = 10):
            super().__init__(parent, bd=0, highlightthickness=0,
                             bg=parent.cget("bg"))
            self._fill = fill
            self._r    = radius
            self._px   = padx
            self._py   = pady
            self._busy = False
            self.inner = tk.Frame(self, bg=fill)
            self._wid  = self.create_window(padx, pady,
                                             window=self.inner, anchor="nw")
            self.inner.bind("<Configure>", self._on_resize)

        def _on_resize(self, _=None) -> None:
            if self._busy:
                return
            self._busy = True
            try:
                self.update_idletasks()
                iw = max(self.inner.winfo_reqwidth(),  10)
                ih = max(self.inner.winfo_reqheight(), 10)
                cw = iw + self._px * 2
                ch = ih + self._py * 2
                self.configure(width=cw, height=ch)
                self.delete("bg")
                r = min(self._r, cw // 2, ch // 2)
                pts = [r,    0,    cw-r, 0,    cw,   0,    cw,   r,
                       cw,   ch-r, cw,   ch,   cw-r, ch,   r,    ch,
                       0,    ch,   0,    ch-r, 0,    r,    0,    0]
                self.create_polygon(pts, smooth=True,
                                    fill=self._fill, outline=_GBORDER, width=1, tags="bg")
                self.tag_lower("bg")
                self.itemconfigure(self._wid, width=iw)
            finally:
                self._busy = False

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("NOVA")
        self.root.geometry("1200x760")
        self.root.configure(bg=_BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Runtime-only state (not persisted to disk)
        self.provider_var = tk.StringVar(value="OpenAI")
        self.api_key_var = tk.StringVar()
        self.model_var = tk.StringVar(value="gpt-4o-mini")
        self.temperature_var = tk.StringVar(value="0.7")
        self.max_tokens_var = tk.StringVar(value="2048")
        self.top_p_var = tk.StringVar(value="1.0")
        self.status_var = tk.StringVar(value="Ready")
        self.proxy_var = tk.StringVar()

        self.openai_models = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1",
        ]
        self.gemini_models = [
            "gemini-3.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
        ]
        self.model_options = self.openai_models

        self._thinking = False
        self._think_frame = 0
        self._think_job: str | None = None
        self._stream_segs:   list  = []
        self._stream_seg_i:  int   = 0
        self._stream_char_i: int   = 0
        self._streaming:     bool  = False
        self._stream_widget: object = None

        self._build_ui()
        # Silently pre-fill proxy from system settings after the window opens
        self.root.after(200, lambda: self._autodetect_proxy(silent=True))

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=0, minsize=290)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        # Animated gradient backdrop – sits behind all grid widgets
        self._bg_canvas = tk.Canvas(self.root, bg=_BG, highlightthickness=0, bd=0)
        self._bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.after(100, self._animate_bg)

        # Sidebar wrapped in a Canvas so it can scroll when content overflows
        _sb = tk.Canvas(self.root, bg=_PANEL, highlightthickness=0, bd=0)
        _sb.grid(row=0, column=0, sticky="nsew")
        self.settings_frame = tk.Frame(_sb, bg=_PANEL)
        _wid = _sb.create_window(0, 0, window=self.settings_frame, anchor="nw")
        self.settings_frame.bind(
            "<Configure>",
            lambda e: (
                _sb.configure(scrollregion=_sb.bbox("all")),
                _sb.itemconfigure(_wid, width=_sb.winfo_width()),
            )
        )
        _sb.bind("<Configure>", lambda e: _sb.itemconfigure(_wid, width=e.width))
        _mw = lambda e: _sb.yview_scroll(-1 * (e.delta // 120), "units")
        _sb.bind("<MouseWheel>", _mw)
        self.settings_frame.bind("<MouseWheel>", _mw, add="+")

        self.chat_frame = tk.Frame(self.root, bg=_BG, bd=0)
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        status_bar = tk.Frame(self.root, bg=_CARD, height=28)
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_label = tk.Label(
            status_bar, textvariable=self.status_var,
            anchor="w", bg=_CARD, fg=_FG2,
            font=("Segoe UI", 9), padx=14, pady=5,
        )
        self.status_label.pack(side="left")
        # Accent progress bar – bounces during API calls
        self._prog_canvas = tk.Canvas(status_bar, height=3, bg=_CARD,
                                       highlightthickness=0)
        self._prog_canvas.pack(side="bottom", fill="x")
        self._prog_bar   = self._prog_canvas.create_rectangle(0, 0, 0, 3,
                                                               fill=_ACCENT, width=0)
        self._prog_phase = 0.0
        self._prog_job   = None

        self._build_settings_panel()
        self._build_chat_panel()

    def _build_settings_panel(self) -> None:
        s = self.settings_frame

        # ── App header ──────────────────────────────────────────────────────
        header = tk.Frame(s, bg="#0a1830", pady=14, padx=18)
        header.pack(fill="x")
        tk.Label(header, text="AI ChatBot", bg="#0a1830", fg=_FG,
                 font=("Segoe UI Semibold", 14)).pack(anchor="w")
        self.subtitle_label = tk.Label(
            header, text="OpenAI API + generation controls",
            bg="#0a1830", fg=_FG2, font=("Segoe UI", 9))
        self.subtitle_label.pack(anchor="w", pady=(2, 0))
        tk.Frame(s, bg=_DIVIDER, height=1).pack(fill="x")

        p = {"padx": 16}

        # ── Provider ────────────────────────────────────────────────────────
        self._section_header(s, "PROVIDER")
        self.provider_menu = tk.OptionMenu(
            s, self.provider_var, "OpenAI", "Google Gemini",
            command=self._on_provider_change,
        )
        self._style_menu(self.provider_menu)
        self.provider_menu.pack(fill="x", **p, pady=(0, 6))

        # ── API Key ─────────────────────────────────────────────────────────
        self._section_header(s, "API KEY")
        key_row = tk.Frame(s, bg=_PANEL)
        key_row.pack(fill="x", **p, pady=(0, 2))
        key_row.grid_columnconfigure(0, weight=1)

        self.api_key_entry = tk.Entry(
            key_row, textvariable=self.api_key_var, show="*",
            bg=_INPUT, fg=_FG, insertbackground=_FG,
            relief="flat", font=("Consolas", 10),
        )
        self.api_key_entry.grid(row=0, column=0, sticky="ew", ipady=5)
        # auto-connect on paste; delay lets the paste land in the field first
        self.api_key_entry.bind("<<Paste>>", lambda e: self.root.after(100, self._on_connect))

        self._btn(key_row, "X", self._clear_api_key, width=2).grid(
            row=0, column=1, padx=(4, 0))
        self._btn(key_row, "Connect", self._on_connect,
                  bg=_ACCENT, fg="#ffffff", hover_bg=_ACCENT_H, hover_fg="#ffffff",
                  width=8).grid(row=0, column=2, padx=(4, 0))

        self.api_key_hint = tk.Label(
            s, text="OpenAI key starts with  sk-...",
            bg=_PANEL, fg=_FG3, font=("Segoe UI", 8), anchor="w")
        self.api_key_hint.pack(fill="x", **p, pady=(2, 8))

        # ── Model ────────────────────────────────────────────────────────────
        self._section_header(s, "MODEL")
        self.model_menu = tk.OptionMenu(s, self.model_var, *self.model_options)
        self._style_menu(self.model_menu)
        self.model_menu.pack(fill="x", **p, pady=(0, 6))

        # ── Generation ───────────────────────────────────────────────────────
        self._section_header(s, "GENERATION")
        self._field(s, "Temperature  (0 - 2)", self.temperature_var)
        self._field(s, "Max Tokens  (> 0)", self.max_tokens_var)
        self._field(s, "Top P  (0 - 1)", self.top_p_var)

        # ── System Message ───────────────────────────────────────────────────
        self._section_header(s, "SYSTEM MESSAGE")
        self.system_message_text = tk.Text(
            s, height=5, wrap="word",
            bg=_INPUT, fg=_FG, insertbackground=_FG,
            relief="flat", font=("Segoe UI", 9), padx=8, pady=6,
        )
        self.system_message_text.insert(
            "1.0",
            "You are NOVA, an advanced AI assistant with a sleek, futuristic personality — "
            "think of yourself as a next-generation digital companion, calm, sharp, and highly capable.\n\n"
            "IDENTITY & TONE:\n"
            "- Speak with quiet confidence and warmth — never robotic, never overly formal.\n"
            "- Use clear, modern language. Avoid jargon unless the user is clearly technical.\n"
            "- Add subtle personality (a touch of wit, curiosity) without being distracting.\n\n"
            "RESPONSE STYLE:\n"
            "- Answer the user's core question in the first 1-2 sentences before adding detail.\n"
            "- Keep responses concise by default; expand only when the user asks for depth.\n"
            "- Use short paragraphs or bullet points for multi-part answers — avoid dense walls of text.\n"
            "- When uncertain, say so plainly rather than guessing.\n\n"
            "USER EXPERIENCE:\n"
            "- If a request is ambiguous, ask one clear clarifying question instead of assuming.\n"
            "- Proactively suggest a relevant next step or follow-up when it adds value, but don't overdo it.\n"
            "- Mirror the user's energy — casual questions get casual, friendly answers; "
            "technical questions get precise, structured ones.\n\n"
            "BOUNDARIES:\n"
            "- Stay honest and transparent about your limitations as an AI.\n"
            "- Never fabricate facts, sources, or capabilities you don't have."
        )
        self.system_message_text.pack(fill="x", **p, pady=(0, 8))

        # ── Proxy ────────────────────────────────────────────────────────────
        self._section_header(s, "PROXY  (optional)")
        proxy_row = tk.Frame(s, bg=_PANEL)
        proxy_row.pack(fill="x", **p, pady=(0, 2))
        proxy_row.grid_columnconfigure(0, weight=1)
        self.proxy_entry = tk.Entry(
            proxy_row, textvariable=self.proxy_var,
            bg=_INPUT, fg=_FG, insertbackground=_FG,
            relief="flat", font=("Segoe UI", 9),
        )
        self.proxy_entry.grid(row=0, column=0, sticky="ew", ipady=4)
        self._btn(proxy_row, "Auto-detect", self._autodetect_proxy, width=11).grid(
            row=0, column=1, padx=(4, 0))
        tk.Label(s, text="e.g. http://proxy.company.com:8080",
                 bg=_PANEL, fg=_FG3, font=("Segoe UI", 8), anchor="w",
                 ).pack(fill="x", **p, pady=(2, 10))

        self._btn(s, "Clear Chat", self._clear_chat,
                  bg="#182840", hover_bg="#1e3250").pack(anchor="e", **p, pady=(0, 12))

    def _build_chat_panel(self) -> None:
        cf = self.chat_frame

        # ── Chat header ──────────────────────────────────────────────────────
        chat_header = tk.Frame(cf, bg=_CARD, pady=11, padx=18)
        chat_header.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(chat_header, text="NOVA", bg=_CARD, fg=_ACCENT,
                 font=("Segoe UI Semibold", 14)).pack(side="left")
        tk.Label(chat_header, text=" · AI Assistant", bg=_CARD, fg=_FG2,
                 font=("Segoe UI", 10)).pack(side="left")
        self.model_badge = tk.Label(
            chat_header, text=self.model_var.get(),
            bg=_BTN, fg=_ACCENT_H, font=("Segoe UI", 9), padx=8, pady=2)
        self.model_badge.pack(side="left", padx=(10, 0))
        self.model_var.trace_add("write", self._update_model_badge)

        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=0)
        cf.grid_rowconfigure(0, weight=0)
        cf.grid_rowconfigure(1, weight=1)
        cf.grid_rowconfigure(2, weight=0)
        cf.grid_rowconfigure(3, weight=0)

        # ── Transcript ───────────────────────────────────────────────────────
        # Scrollable bubble list replacing the flat Text widget
        self._chat_canvas = tk.Canvas(cf, bg=_BG, highlightthickness=0, bd=0)
        self._chat_canvas.grid(row=1, column=0, sticky="nsew")

        _csb = tk.Scrollbar(cf, orient="vertical", command=self._chat_canvas.yview,
                             width=6, troughcolor=_BG, bg=_BTN, relief="flat")
        _csb.grid(row=1, column=1, sticky="ns")
        self._chat_canvas.configure(yscrollcommand=_csb.set)

        self._chat_inner = tk.Frame(self._chat_canvas, bg=_BG)
        _cwin = self._chat_canvas.create_window(0, 0, window=self._chat_inner, anchor="nw")
        self._chat_inner.bind(
            "<Configure>",
            lambda e: self._chat_canvas.configure(
                scrollregion=self._chat_canvas.bbox("all")),
        )
        self._chat_canvas.bind(
            "<Configure>",
            lambda e: (
                self._chat_canvas.itemconfigure(_cwin, width=e.width),
                self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all")),
            ),
        )
        self._chat_mw = lambda e: self._chat_canvas.yview_scroll(
            -1 * (e.delta // 120), "units")
        self._chat_canvas.bind("<MouseWheel>", self._chat_mw)
        self._chat_inner.bind("<MouseWheel>", self._chat_mw, add="+")

        # ── Thinking indicator ────────────────────────────────────────────────
        think_wrap = tk.Frame(cf, bg=_BG, pady=3)
        think_wrap.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.thinking_label = tk.Label(
            think_wrap, text="", bg=_BG, fg=_FG2,
            font=("Segoe UI", 9), padx=22, anchor="w")
        self.thinking_label.pack(fill="x")

        # ── Input bar ────────────────────────────────────────────────────────
        input_frame = tk.Frame(cf, bg=_CARD, padx=16, pady=12)
        input_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_text = tk.Text(
            input_frame, height=4, wrap="word",
            bg=_INPUT, fg=_FG, insertbackground=_FG,
            relief="flat", padx=12, pady=10,
            font=("Segoe UI", 11),
        )
        self.input_text.grid(row=0, column=0, sticky="ew")
        self.input_text.bind("<Return>", self._send_hotkey)
        self.input_text.bind("<Shift-Return>", self._newline_hotkey)
        self.input_text.bind("<FocusIn>",  lambda e: self._focus_bar(True))
        self.input_text.bind("<FocusOut>", lambda e: self._focus_bar(False))

        self.send_button = self._RoundBtn(
            input_frame, text="Send  \u203a", command=self._on_send,
            bg=_ACCENT, fg="#ffffff",
            hover_bg=_ACCENT_H, hover_fg="#ffffff",
            padx=22, pady=10, font=("Segoe UI Semibold", 11),
        )
        self.send_button.grid(row=0, column=1, padx=(10, 0), sticky="s")

        tk.Label(input_frame, text="Enter to send  \u2502  Shift+Enter for new line",
                 bg=_CARD, fg=_FG3, font=("Segoe UI", 8),
                 ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Accent line animates full-width on focus
        self._inp_border = tk.Canvas(input_frame, height=2, bg=_CARD,
                                      highlightthickness=0)
        self._inp_border.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        self._inp_line   = self._inp_border.create_rectangle(0, 0, 0, 2,
                                                              fill=_ACCENT, width=0)

        self._append_message(
            "assistant",
            "Welcome. Select a provider (OpenAI or Google Gemini), enter your API key, choose a model, then send a message.",
        )

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _section_header(self, parent: tk.Widget, text: str) -> None:
        row = tk.Frame(parent, bg=_PANEL, pady=7)
        row.pack(fill="x", padx=16)
        tk.Label(row, text=text, bg=_PANEL, fg=_ACCENT,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(side="left")
        tk.Frame(row, bg=_DIVIDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=1)

    def _field(self, parent: tk.Widget, label: str, var: tk.StringVar) -> None:
        tk.Label(parent, text=label, bg=_PANEL, fg=_FG2,
                 font=("Segoe UI", 9), anchor="w",
                 ).pack(fill="x", padx=16, pady=(0, 1))
        tk.Entry(parent, textvariable=var,
                 bg=_INPUT, fg=_FG, insertbackground=_FG,
                 relief="flat", font=("Segoe UI", 10),
                 ).pack(fill="x", padx=16, pady=(0, 7), ipady=4)

    def _btn(self, parent: tk.Widget, text: str, command,
             bg: str = _BTN, fg: str = _FG,
             hover_bg: str = _BTN_HV, hover_fg: str = _FG,
             width: int | None = None) -> "ChatbotApp._RoundBtn":
        return self._RoundBtn(parent, text=text, command=command,
                              bg=bg, fg=fg, hover_bg=hover_bg, hover_fg=hover_fg,
                              padx=10, pady=4)

    def _style_menu(self, menu: tk.OptionMenu) -> None:
        menu.configure(
            bg=_INPUT, fg=_FG,
            activebackground=_BTN_HV, activeforeground=_FG,
            relief="flat", highlightthickness=0, pady=6, bd=0,
        )
        menu["menu"].configure(
            bg=_CARD, fg=_FG,
            activebackground=_ACCENT, activeforeground="#ffffff",
            relief="flat",
        )
        self._bind_hover(menu, _INPUT, _INPUT_HV)

    def _bind_hover(self, widget: tk.Widget, normal: str, hovered: str) -> None:
        """Smooth 8-frame bg colour transition on mouse enter / leave (~110 ms)."""
        job: list = [None]

        def _lerp(a: str, b: str, t: float) -> str:
            r = round(int(a[1:3], 16) * (1 - t) + int(b[1:3], 16) * t)
            g = round(int(a[3:5], 16) * (1 - t) + int(b[3:5], 16) * t)
            bv = round(int(a[5:7], 16) * (1 - t) + int(b[5:7], 16) * t)
            return f"#{r:02x}{g:02x}{bv:02x}"

        def _run(start: str, end: str, step: int = 0) -> None:
            if job[0]:
                try:
                    widget.after_cancel(job[0])
                except Exception:
                    pass
            if step > 8:
                return
            try:
                widget.configure(bg=_lerp(start, end, step / 8))
            except tk.TclError:
                return
            job[0] = widget.after(14, lambda: _run(start, end, step + 1))

        widget.bind("<Enter>", lambda e: _run(widget.cget("bg"), hovered))
        widget.bind("<Leave>", lambda e: _run(widget.cget("bg"), normal))

    def _update_model_badge(self, *_) -> None:
        try:
            self.model_badge.configure(text=self.model_var.get())
        except Exception:
            pass

    # ── Chat bubble helpers ───────────────────────────────────────────────────

    def _configure_md_tags(self, w: tk.Text) -> None:
        w.tag_configure("body",         foreground=_FG,       font=("Segoe UI", 11))
        w.tag_configure("err_body",     foreground="#fca5a5", font=("Segoe UI", 11))
        w.tag_configure("md_bold",      foreground=_FG,       font=("Segoe UI", 11, "bold"))
        w.tag_configure("md_italic",    foreground=_FG,       font=("Segoe UI", 11, "italic"))
        w.tag_configure("md_code",      foreground="#a5f3fc", font=("Consolas", 10),
                        background="#0d1f38")
        w.tag_configure("md_codeblock", foreground="#a5f3fc", font=("Consolas", 9),
                        background="#0d1f38", spacing1=4, spacing3=4)
        w.tag_configure("md_h1", foreground=_FG, font=("Segoe UI Semibold", 17),
                        spacing1=10, spacing3=5)
        w.tag_configure("md_h2", foreground=_FG, font=("Segoe UI Semibold", 14),
                        spacing1=8,  spacing3=4)
        w.tag_configure("md_h3", foreground=_FG, font=("Segoe UI Semibold", 12),
                        spacing1=5,  spacing3=2)
        w.tag_configure("md_bullet", foreground=_ACCENT, font=("Segoe UI", 11, "bold"))
        w.tag_configure("md_num",    foreground=_ACCENT, font=("Segoe UI", 11, "bold"))
        w.tag_configure("md_hr",     foreground=_FG3,   font=("Segoe UI", 8))

    def _make_text_bubble(self, parent: tk.Frame, bg: str) -> tk.Text:
        w = tk.Text(
            parent, wrap="word", bg=bg, fg=_FG,
            relief="flat", font=("Segoe UI", 11),
            padx=0, pady=4, height=1, width=42,
            state="disabled", cursor="arrow",
            highlightthickness=0, bd=0,
        )
        self._configure_md_tags(w)
        w.bind("<MouseWheel>", self._chat_mw, add="+")
        return w

    def _resize_text_height(self, w: tk.Text) -> None:
        try:
            # displaylines counts visual lines after word-wrap, not just \n lines
            dl = w.count("1.0", "end", "displaylines")
            lines = dl[0] if dl else int(w.index("end-1c").split(".")[0])
            w.configure(height=max(1, lines))
        except Exception:
            pass

    def _finalize_bubble(self, w: tk.Text) -> None:
        """One-shot accurate resize after widget fully renders at its final width."""
        try:
            w.update_idletasks()
            dl = w.count("1.0", "end", "displaylines")
            lines = dl[0] if dl else int(w.index("end-1c").split(".")[0])
            w.configure(height=max(1, lines))
            self._scroll_chat_bottom()
        except Exception:
            pass

    def _fit_text_bubble(self, w: tk.Text) -> None:
        """Shrink width to actual content so the bubble hugs its text."""
        try:
            content = w.get("1.0", "end-1c")
            if not content.strip():
                return
            f = tkfont.Font(font=("Segoe UI", 11))
            max_px = max(
                (f.measure(line) for line in content.split("\n") if line),
                default=60,
            )
            max_px = min(max_px + 20, 520)
            # tk.Text sizes its width using the "0" glyph as the unit
            char_unit = max(f.measure("0"), 1)
            w.configure(width=max(4, -(-max_px // char_unit)))  # ceiling div
        except Exception:
            pass

    def _scroll_chat_bottom(self) -> None:
        self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))
        self._chat_canvas.yview_moveto(1.0)

    def _add_bubble_user(self, text: str) -> None:
        _UBG = "#1a2d44"
        row = tk.Frame(self._chat_inner, bg=_BG)
        row.pack(fill="x", padx=16, pady=(6, 2))
        row.bind("<MouseWheel>", self._chat_mw, add="+")
        bubble = self._RoundFrame(row, fill=_UBG, radius=18)
        bubble.pack(side="right")
        for w in (bubble, bubble.inner):
            w.bind("<MouseWheel>", self._chat_mw, add="+")
        lbl_name = tk.Label(bubble.inner, text="You", bg=_UBG,
                            fg=_USER, font=("Segoe UI Semibold", 9), anchor="e")
        lbl_name.pack(anchor="e")
        lbl_name.bind("<MouseWheel>", self._chat_mw, add="+")
        lbl_text = tk.Label(bubble.inner, text=text, bg=_UBG, fg=_FG,
                            font=("Segoe UI", 11), wraplength=440,
                            justify="right", anchor="e")
        lbl_text.pack(anchor="e")
        lbl_text.bind("<MouseWheel>", self._chat_mw, add="+")
        self._scroll_chat_bottom()

    def _add_bubble_asst_frame(self) -> tk.Text:
        _ABG = "#1a2d44"
        row = tk.Frame(self._chat_inner, bg=_BG)
        row.pack(fill="x", padx=16, pady=(6, 2))
        row.bind("<MouseWheel>", self._chat_mw, add="+")
        bubble = self._RoundFrame(row, fill=_ABG, radius=18)
        bubble.pack(side="left")
        for w in (bubble, bubble.inner):
            w.bind("<MouseWheel>", self._chat_mw, add="+")
        lbl = tk.Label(bubble.inner, text="Assistant", bg=_ABG, fg=_ASST,
                       font=("Segoe UI Semibold", 9), anchor="w")
        lbl.pack(anchor="w")
        lbl.bind("<MouseWheel>", self._chat_mw, add="+")
        w = self._make_text_bubble(bubble.inner, _ABG)
        w.pack(anchor="w")
        return w

    def _add_bubble_error(self, text: str) -> None:
        _EB = "#3d1010"
        row = tk.Frame(self._chat_inner, bg=_BG)
        row.pack(fill="x", padx=16, pady=(6, 2))
        row.bind("<MouseWheel>", self._chat_mw, add="+")
        bubble = self._RoundFrame(row, fill=_EB, radius=18)
        bubble.pack(side="left")
        for w in (bubble, bubble.inner):
            w.bind("<MouseWheel>", self._chat_mw, add="+")
        lbl = tk.Label(bubble.inner, text="Error", bg=_EB, fg=_ERR,
                       font=("Segoe UI Semibold", 9))
        lbl.pack(anchor="w")
        lbl.bind("<MouseWheel>", self._chat_mw, add="+")
        lbl2 = tk.Label(bubble.inner, text=text, bg=_EB, fg="#fca5a5",
                        font=("Segoe UI", 11), wraplength=440,
                        justify="left", anchor="w")
        lbl2.pack(anchor="w")
        lbl2.bind("<MouseWheel>", self._chat_mw, add="+")
        self._scroll_chat_bottom()

    # ── Thinking animation ────────────────────────────────────────────────────

    def _start_thinking(self) -> None:
        self._thinking = True
        self._think_frame = 0
        self._prog_start()
        self._tick_thinking()

    def _tick_thinking(self) -> None:
        if not self._thinking:
            return
        sym = self._SPIN[self._think_frame % len(self._SPIN)]
        self.thinking_label.configure(text=f"  {sym}  Thinking...")
        self._think_frame += 1
        self._think_job = self.root.after(90, self._tick_thinking)

    def _stop_thinking(self) -> None:
        self._thinking = False
        if self._think_job:
            try:
                self.root.after_cancel(self._think_job)
            except Exception:
                pass
            self._think_job = None
        self.thinking_label.configure(text="")
        self._prog_stop()

    # ── Focus-bar / progress-bar / typewriter animations ─────────────────────

    def _focus_bar(self, expand: bool) -> None:
        target = self._inp_border.winfo_width() if expand else 0
        coords = self._inp_border.coords(self._inp_line)
        start  = float(coords[2]) if coords else 0.0
        steps  = 10
        delta  = (target - start) / steps

        def _step(w: float, n: int) -> None:
            try:
                self._inp_border.coords(self._inp_line, 0, 0, max(0.0, w), 2)
            except Exception:
                return
            if n < steps:
                self.root.after(10, lambda: _step(w + delta, n + 1))

        _step(start + delta, 1)

    def _prog_start(self) -> None:
        self._prog_phase = 0.0
        self._prog_tick()

    def _prog_stop(self) -> None:
        if self._prog_job:
            try: self.root.after_cancel(self._prog_job)
            except Exception: pass
            self._prog_job = None
        try:
            self._prog_canvas.coords(self._prog_bar, 0, 0, 0, 3)
        except Exception:
            pass

    def _prog_tick(self) -> None:
        if not self._thinking:
            self._prog_stop()
            return
        self._prog_phase += 0.055
        t   = (math.sin(self._prog_phase) + 1) / 2
        w   = max(self._prog_canvas.winfo_width(), 4)
        bw  = w * (0.12 + t * 0.45)
        bx  = (w - bw) * t
        self._prog_canvas.coords(self._prog_bar, bx, 0, bx + bw, 3)
        self._prog_job = self.root.after(16, self._prog_tick)

    def _animate_bg(self) -> None:
        self._bg_t = getattr(self, "_bg_t", 0.0) + 0.006
        c = self._bg_canvas
        c.delete("orb")
        W = c.winfo_width()  or 1200
        H = c.winfo_height() or 760
        br, bg_, bb = 0x0d, 0x11, 0x17   # _BG components
        blobs = [
            (W * 0.12 + math.sin(self._bg_t * 0.7)  * 90,
             H * 0.38 + math.cos(self._bg_t * 0.5)  * 70,
             340, 0x0d, 0x2a, 0x60),
            (W * 0.88 + math.sin(self._bg_t * 0.4 + 2.1) * 110,
             H * 0.22 + math.cos(self._bg_t * 0.55 + 1.3) * 80,
             290, 0x18, 0x0a, 0x48),
            (W * 0.55 + math.sin(self._bg_t * 0.35 + 4.2) * 130,
             H * 0.78 + math.cos(self._bg_t * 0.45 + 3.1) * 65,
             260, 0x08, 0x28, 0x38),
        ]
        for cx, cy, r, cr, cg, cb in blobs:
            for i in range(7, 0, -1):
                t = i / 7
                nr = int(cr * t + br * (1 - t))
                ng = int(cg * t + bg_ * (1 - t))
                nb = int(cb * t + bb * (1 - t))
                ri = r * i / 7
                c.create_oval(cx - ri, cy - ri, cx + ri, cy + ri,
                              fill=f"#{nr:02x}{ng:02x}{nb:02x}", outline="", tags="orb")
        self.root.after(40, self._animate_bg)

    def _stream_text(self, text: str) -> None:
        self._stream_widget = self._add_bubble_asst_frame()
        self._stream_segs   = self._parse_md(text)
        self._stream_seg_i  = 0
        self._stream_char_i = 0
        self._streaming     = True
        self._do_stream()

    def _do_stream(self) -> None:
        if not self._streaming:
            return
        w = self._stream_widget
        if self._stream_seg_i >= len(self._stream_segs):
            w.configure(state="normal")
            w.insert("end", "\n")
            w.configure(state="disabled")
            self._fit_text_bubble(w)
            self._resize_text_height(w)
            self._scroll_chat_bottom()
            self._streaming = False
            self.root.after(50, lambda: self._finalize_bubble(w))
            return
        seg_text, seg_tag = self._stream_segs[self._stream_seg_i]
        end_i = min(self._stream_char_i + 10, len(seg_text))
        chunk = seg_text[self._stream_char_i:end_i]
        if chunk:
            w.configure(state="normal")
            w.insert("end", chunk, seg_tag)
            w.configure(state="disabled")
            self._resize_text_height(w)
            self._stream_tick = getattr(self, "_stream_tick", 0) + 1
            if self._stream_tick % 5 == 0:  # throttle scroll, not height
                self._scroll_chat_bottom()
        self._stream_char_i = end_i
        if self._stream_char_i >= len(seg_text):
            self._stream_seg_i  += 1
            self._stream_char_i  = 0
        self.root.after(10, self._do_stream)

    @staticmethod
    def _parse_md(text: str) -> list[tuple[str, str]]:
        """Tokenise markdown text into (segment, tag) pairs."""
        segs: list[tuple[str, str]] = []

        # Inline: **bold** / __bold__ / *italic* / _italic_ / `code`
        _INLINE = re.compile(
            r'\*\*(.+?)\*\*'           # **bold**
            r'|__(.+?)__'              # __bold__
            r'|\*(?!\s)(.+?)(?<!\s)\*' # *italic*
            r'|_(?!\s)(.+?)(?<!\s)_'   # _italic_
            r'|`(.+?)`',               # `code`
            re.DOTALL,
        )

        def _inline(s: str, base: str = "body") -> None:
            last = 0
            for m in _INLINE.finditer(s):
                if m.start() > last:
                    segs.append((s[last:m.start()], base))
                g1, g2, g3, g4, g5 = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                if   g1 is not None: segs.append((g1, "md_bold"))
                elif g2 is not None: segs.append((g2, "md_bold"))
                elif g3 is not None: segs.append((g3, "md_italic"))
                elif g4 is not None: segs.append((g4, "md_italic"))
                elif g5 is not None: segs.append((g5, "md_code"))
                last = m.end()
            if last < len(s):
                segs.append((s[last:], base))

        lines = text.strip().split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Fenced code block
            if line.strip().startswith("```"):
                i += 1
                code: list[str] = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i])
                    i += 1
                segs.append(("\n".join(code), "md_codeblock"))
                segs.append(("\n", "body"))
                i += 1
                continue

            # ATX headings
            m1 = re.match(r"^(#{1,3}) (.+)", line)
            if m1:
                level = len(m1.group(1))
                tag   = f"md_h{level}"
                _inline(m1.group(2), tag)
                segs.append(("\n", "body"))
                i += 1
                continue

            # Horizontal rule
            if re.fullmatch(r"[\-\*\_]{3,}\s*", line):
                segs.append(("\n────────────────────────\n", "md_hr"))
                i += 1
                continue

            # Unordered bullet
            bm = re.match(r"^([ \t]*)[\-\*\+] (.*)", line)
            if bm:
                indent = len(bm.group(1))
                segs.append(("  " + "  " * (indent // 2) + "• ", "md_bullet"))
                _inline(bm.group(2))
                segs.append(("\n", "body"))
                i += 1
                continue

            # Ordered list
            nm = re.match(r"^([ \t]*)(\d+)\. (.*)", line)
            if nm:
                indent = len(nm.group(1))
                segs.append(("  " + "  " * (indent // 2) + nm.group(2) + ".  ", "md_num"))
                _inline(nm.group(3))
                segs.append(("\n", "body"))
                i += 1
                continue

            # Empty line → blank line gap
            if line.strip() == "":
                segs.append(("\n", "body"))
                i += 1
                continue

            _inline(line)
            segs.append(("\n", "body"))
            i += 1

        return segs

    def _autodetect_proxy(self, silent: bool = False) -> None:
        from urllib.request import getproxies
        proxies = getproxies()
        url = proxies.get("https") or proxies.get("http") or ""
        if not url:
            url = self._extract_pac_proxy()
        if url:
            self.proxy_var.set(url)
            if not silent:
                self._set_status(f"Proxy auto-detected: {url}")
        elif not silent:
            self._set_status(
                "No proxy found automatically. "
                "Check: Control Panel \u2192 Internet Options \u2192 Connections \u2192 LAN Settings"
            )

    def _extract_pac_proxy(self) -> str:
        """Read AutoConfigURL from registry and extract the first PROXY entry from the PAC file."""
        import re
        pac_url = ""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            pac_url, _ = winreg.QueryValueEx(key, "AutoConfigURL")
        except Exception:
            pass
        if not pac_url:
            return ""
        try:
            with request.urlopen(pac_url, timeout=5) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            matches = re.findall(r'PROXY\s+([\w.\-]+:\d+)', content)
            if matches:
                return f"http://{matches[0]}"
        except Exception:
            pass
        return ""

    def _on_provider_change(self, provider: str) -> None:
        models = self.gemini_models if provider == "Google Gemini" else self.openai_models
        menu = self.model_menu["menu"]
        menu.delete(0, "end")
        for m in models:
            menu.add_command(label=m, command=tk._setit(self.model_var, m))
        self.model_var.set(models[0])
        self.subtitle_label.configure(
            text="Google Gemini API + generation controls" if provider == "Google Gemini"
            else "OpenAI API + generation controls"
        )
        self.api_key_hint.configure(
            text="Gemini: paste your Google AI Studio key" if provider == "Google Gemini"
            else "OpenAI key starts with  sk-..."
        )

    def _validate_key_format(self, api_key: str, provider: str) -> str | None:
        if provider == "OpenAI" and not api_key.startswith("sk-"):
            return "OpenAI API keys start with 'sk-'. Please check you selected the right provider."
        return None

    def _clear_api_key(self) -> None:
        self.api_key_var.set("")
        self._set_status("Ready")

    def _on_connect(self) -> None:
        api_key = self.api_key_var.get().strip()
        provider = self.provider_var.get()
        if not api_key:
            messagebox.showwarning("Missing API Key", f"Please enter your {provider} API key.")
            return
        err = self._validate_key_format(api_key, provider)
        if err:
            messagebox.showwarning("Invalid Key Format", err)
            return
        self._set_status("Connecting...")
        threading.Thread(target=self._test_connection, args=(api_key, provider), daemon=True).start()

    def _test_connection(self, api_key: str, provider: str) -> None:
        proxy_url = self.proxy_var.get().strip()
        try:
            if provider == "Google Gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                req = request.Request(url, method="GET")
            else:
                req = request.Request(
                    "https://api.openai.com/v1/models",
                    method="GET",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            if proxy_url:
                opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url}))
                ctx = opener.open(req, timeout=15)
            else:
                ctx = request.urlopen(req, timeout=15)
            with ctx:
                pass
            self.root.after(0, lambda: self._set_status("Connected ✓  API key is valid", "#86efac"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            msg = self._format_http_error(exc.code, details)
            self.root.after(0, lambda: self._set_status(f"Connection failed: {msg}", "#fca5a5"))
        except error.URLError as exc:
            reason = exc.reason
            # socket.timeout is a subclass of TimeoutError and gets wrapped in URLError
            if isinstance(reason, TimeoutError):
                self.root.after(0, lambda: self._set_status("Connection timed out. Check your internet connection or enter a Proxy URL in Settings.", "#fca5a5"))
            else:
                hint = ""
                if isinstance(reason, OSError) and getattr(reason, "winerror", None) == 10060:
                    hint = (
                        "\nDNS resolved but the connection was blocked."
                        "\nFix: connect via a VPN, or enter a Proxy URL in Settings if your network requires one."
                    )
                elif isinstance(reason, OSError) and getattr(reason, "winerror", None) == 10061:
                    hint = "\nTip: Connection refused. The API endpoint may be blocked."
                self.root.after(0, lambda: self._set_status(f"Network error: {reason}{hint}", "#fca5a5"))
        except Exception as exc:
            self.root.after(0, lambda: self._set_status(f"Unexpected error: {exc}", "#fca5a5"))

    def _send_hotkey(self, event: tk.Event) -> str:
        self._on_send()
        return "break"

    def _newline_hotkey(self, event: tk.Event) -> str:  # Shift+Enter inserts a newline
        self.input_text.insert("insert", "\n")
        return "break"

    def _append_message(self, role: str, text: str) -> None:
        if role == "user":
            self._add_bubble_user(text.strip())
        elif role == "assistant":
            w = self._add_bubble_asst_frame()
            segs = self._parse_md(text.strip())
            w.configure(state="normal")
            for seg_text, seg_tag in segs:
                w.insert("end", seg_text, seg_tag)
            w.configure(state="disabled")
            self._fit_text_bubble(w)
            self._resize_text_height(w)
            self._scroll_chat_bottom()
            self.root.after(50, lambda: self._finalize_bubble(w))
        else:
            self._add_bubble_error(text.strip())

    def _set_status(self, text: str, color: str = _FG2) -> None:
        self.status_var.set(text)
        self.status_label.configure(fg=color)

    def _on_send(self) -> None:
        api_key = self.api_key_var.get().strip()
        provider = self.provider_var.get()
        user_text = self.input_text.get("1.0", "end").strip()

        if not api_key:
            messagebox.showwarning("Missing API Key", f"Please enter your {provider} API key.")
            return

        if not user_text:
            return

        err = self._validate_key_format(api_key, provider)
        if err:
            messagebox.showwarning("Invalid Key Format", err)
            return

        try:
            settings = self._collect_settings()
        except ValueError as exc:
            messagebox.showerror("Invalid Settings", str(exc))
            return

        self._append_message("user", user_text)
        self.input_text.delete("1.0", "end")
        self._set_busy(True)
        self._set_status("Sending request...")

        worker = threading.Thread(
            target=self._request_completion,
            args=(api_key, settings, user_text),
            daemon=True,
        )
        worker.start()

    def _collect_settings(self) -> dict:
        model = self.model_var.get().strip()
        if not model:
            raise ValueError("Model is required.")

        try:
            temperature = float(self.temperature_var.get().strip())
        except ValueError as exc:
            raise ValueError("Temperature must be a number.") from exc

        if temperature < 0.0 or temperature > 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0.")

        try:
            max_tokens = int(self.max_tokens_var.get().strip())
        except ValueError as exc:
            raise ValueError("Max tokens must be an integer.") from exc

        if max_tokens <= 0:
            raise ValueError("Max tokens must be greater than 0.")

        try:
            top_p = float(self.top_p_var.get().strip())
        except ValueError as exc:
            raise ValueError("Top P must be a number.") from exc

        if top_p < 0.0 or top_p > 1.0:
            raise ValueError("Top P must be between 0.0 and 1.0.")

        system_message = self.system_message_text.get("1.0", "end").strip()

        return {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "system_message": system_message,
        }

    def _request_completion(self, api_key: str, settings: dict, user_text: str) -> None:
        if self.provider_var.get() == "Google Gemini":
            self._request_gemini_completion(api_key, settings, user_text)
            return
        proxy_url = self.proxy_var.get().strip()
        try:
            messages = []
            if settings["system_message"]:
                messages.append({"role": "system", "content": settings["system_message"]})

            # No memory mode: only system + current user message are sent.
            messages.append({"role": "user", "content": user_text})

            model_name = settings["model"]
            payload = {
                "model": model_name,
                "messages": messages,
            }

            # GPT-5 models use max_completion_tokens and fixed sampling defaults.
            if model_name.startswith("gpt-5"):
                payload["temperature"] = 1
                payload["top_p"] = 1
                payload["max_completion_tokens"] = settings["max_tokens"]
            else:
                payload["temperature"] = settings["temperature"]
                payload["top_p"] = settings["top_p"]
                payload["max_tokens"] = settings["max_tokens"]

            body = json.dumps(payload).encode("utf-8")
            req = request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )

            if proxy_url:
                opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url}))
                response_ctx = opener.open(req, timeout=60)
            else:
                response_ctx = request.urlopen(req, timeout=60)

            with response_ctx as response:
                raw = response.read().decode("utf-8")

            data = json.loads(raw)
            assistant_text = self._extract_assistant_text(data)
            self.root.after(0, lambda: self._on_response_success(assistant_text))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            message = self._format_http_error(exc.code, details)
            self.root.after(0, lambda: self._on_response_error(message))
        except error.URLError as exc:
            reason = exc.reason
            # socket.timeout is a subclass of TimeoutError and gets wrapped in URLError
            if isinstance(reason, TimeoutError):
                self.root.after(0, lambda: self._on_response_error("Request timed out. Check your internet connection or enter a Proxy URL in Settings."))
            else:
                hint = ""
                if isinstance(reason, OSError) and getattr(reason, "winerror", None) == 10060:
                    hint = (
                        "\nDNS resolved but the connection was blocked before reaching OpenAI."
                        "\nFix: connect via a VPN, or enter a Proxy URL in Settings if your network requires one."
                    )
                elif isinstance(reason, OSError) and getattr(reason, "winerror", None) == 10061:
                    hint = "\nTip: Connection refused. The API endpoint may be blocked."
                self.root.after(0, lambda: self._on_response_error(f"Network error: {reason}{hint}"))
        except Exception as exc:
            self.root.after(0, lambda: self._on_response_error(f"Unexpected error: {exc}"))

    def _request_gemini_completion(self, api_key: str, settings: dict, user_text: str) -> None:
        proxy_url = self.proxy_var.get().strip()
        try:
            model_name = settings["model"]
            payload: dict = {
                "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                "generationConfig": {
                    "temperature": settings["temperature"],
                    "maxOutputTokens": settings["max_tokens"],
                    "topP": settings["top_p"],
                },
            }
            if settings["system_message"]:
                payload["system_instruction"] = {"parts": [{"text": settings["system_message"]}]}

            body = json.dumps(payload).encode("utf-8")
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={api_key}"
            )
            req = request.Request(
                url, data=body, method="POST",
                headers={"Content-Type": "application/json"},
            )

            if proxy_url:
                opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url}))
                response_ctx = opener.open(req, timeout=60)
            else:
                response_ctx = request.urlopen(req, timeout=60)

            with response_ctx as response:
                raw = response.read().decode("utf-8")

            data = json.loads(raw)
            assistant_text = self._extract_gemini_text(data)
            self.root.after(0, lambda: self._on_response_success(assistant_text))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            message = self._format_http_error(exc.code, details)
            self.root.after(0, lambda: self._on_response_error(message))
        except error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                self.root.after(0, lambda: self._on_response_error("Request timed out. Check your internet connection or enter a Proxy URL in Settings."))
            else:
                self.root.after(0, lambda: self._on_response_error(f"Network error: {reason}"))
        except Exception as exc:
            self.root.after(0, lambda: self._on_response_error(f"Unexpected error: {exc}"))

    def _extract_gemini_text(self, data: dict) -> str:
        if "error" in data:
            raise ValueError(data["error"].get("message", "Gemini API error"))
        candidates = data.get("candidates")
        if not candidates:
            raise ValueError("No candidates in Gemini response.")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text if text else "[Empty response]"

    def _extract_assistant_text(self, data: dict) -> str:
        choices = data.get("choices")
        if not choices:
            raise ValueError("No choices found in OpenAI response.")

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if isinstance(content, str):
            text = content.strip()
            return text if text else "[Empty response]"

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            text = "\n".join(part.strip() for part in parts if part and part.strip()).strip()
            return text if text else "[Empty response]"

        return "[Unrecognized response format]"

    def _format_http_error(self, status_code: int, details: str) -> str:
        try:
            parsed = json.loads(details)
            api_error = parsed.get("error", {}).get("message", "")
            if api_error:
                return f"API error ({status_code}): {api_error}"
        except Exception:
            pass

        short = details.strip().replace("\n", " ")
        if len(short) > 240:
            short = short[:240] + "..."
        return f"API error ({status_code}): {short or 'No details provided.'}"

    def _on_response_success(self, assistant_text: str) -> None:
        self._set_busy(False)
        self._set_status("Ready")
        self._stream_text(assistant_text)

    def _on_response_error(self, err_text: str) -> None:
        self._append_message("error", err_text)
        self._set_busy(False)
        self._set_status("Ready (last request failed)", "#fca5a5")

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self.send_button.configure(state="disabled", bg="#3a6bd8")
            self._start_thinking()
        else:
            self.send_button.configure(state="normal", bg=_ACCENT)
            self._stop_thinking()

    def _clear_chat(self) -> None:
        for child in self._chat_inner.winfo_children():
            child.destroy()
        self._append_message("assistant", "Chat cleared. No conversation memory is kept.")

    def _on_close(self) -> None:
        # Explicitly clear runtime secret before exit.
        self.api_key_var.set("")
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ChatbotApp(root)
    root.minsize(1000, 660)
    root.mainloop()


if __name__ == "__main__":
    main()

