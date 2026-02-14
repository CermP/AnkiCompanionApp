#!/usr/bin/env python3
"""
AnkiCompanion — Cross-platform GUI for exporting Anki decks to CSV + media.
Works on Windows, macOS, and Linux. Requires Python 3 + tkinter.
Anki must be running with AnkiConnect add-on active.
"""

import json
import urllib.request
import csv
import os
import html
import re
import unicodedata
import base64
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ANKI_URL = "http://127.0.0.1:8765"
APP_TITLE = "Anki Companion"


# ──────────────────────────────────────────────
# AnkiConnect helpers
# ──────────────────────────────────────────────

def anki_request(action, **params):
    """Send a request to AnkiConnect and return the result."""
    payload = json.dumps({
        "action": action,
        "params": params,
        "version": 6
    }).encode("utf-8")
    req = urllib.request.Request(ANKI_URL, payload)
    response = json.load(urllib.request.urlopen(req))
    if response.get("error") is not None:
        raise Exception(response["error"])
    return response["result"]


def fetch_deck_names():
    """Get list of deck names from Anki."""
    return anki_request("deckNames")


# ──────────────────────────────────────────────
# Export logic (same as export_with_media.py)
# ──────────────────────────────────────────────

def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '_', value)


def retrieve_media_from_anki(filename, media_subfolder, media_base_dir):
    target_dir = os.path.join(media_base_dir, media_subfolder)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, filename)

    if os.path.exists(target_path):
        return True

    try:
        result = anki_request("retrieveMediaFile", filename=filename)
    except Exception:
        return False

    if not result:
        return False

    try:
        file_data = base64.b64decode(result)
        with open(target_path, 'wb') as f:
            f.write(file_data)
        return True
    except Exception:
        return False


def process_media_in_text(source_text, media_subfolder, media_base_dir):
    modified_text = source_text
    image_pattern = r'src=["\']([^"\']+\.(jpg|jpeg|png|gif|svg|webp))["\']'
    matches = re.findall(image_pattern, source_text, re.IGNORECASE)

    for match in matches:
        filename = match[0]
        retrieve_media_from_anki(filename, media_subfolder, media_base_dir)
        new_relative_path = f"../media/{media_subfolder}/{filename}"
        modified_text = modified_text.replace(f'src="{filename}"', f'src="{new_relative_path}"')
        modified_text = modified_text.replace(f"src='{filename}'", f"src='{new_relative_path}'")

    return modified_text


def export_deck(deck_name, output_base_dir, media_base_dir, log_fn=print):
    """Export a single deck to CSV with media. Returns card count."""
    log_fn(f"📦 {deck_name}")

    media_subfolder = slugify(deck_name.split("::")[-1])

    try:
        note_ids = anki_request("findNotes", query=f'"deck:{deck_name}"')
    except Exception as e:
        log_fn(f"  ❌ findNotes failed: {e}")
        return 0

    if not note_ids:
        log_fn(f"  ⚠️ No notes found")
        return 0

    try:
        notes_info = anki_request("notesInfo", notes=note_ids)
    except Exception as e:
        log_fn(f"  ❌ notesInfo failed: {e}")
        return 0

    parts = deck_name.split("::")
    if len(parts) == 1:
        matiere = "divers"
        safe_filename = slugify(parts[0])
    else:
        matiere = slugify(parts[0])
        safe_filename = "_".join([slugify(p) for p in parts[1:]])

    matiere_dir = os.path.join(output_base_dir, matiere)
    os.makedirs(matiere_dir, exist_ok=True)

    csv_path = os.path.join(matiere_dir, f"{safe_filename}.csv")

    try:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            count = 0
            for note in notes_info:
                fields_values = []
                for field_obj in note["fields"].values():
                    raw_value = field_obj["value"]
                    clean_value = html.unescape(raw_value)
                    modified_value = process_media_in_text(clean_value, media_subfolder, media_base_dir)
                    fields_values.append(modified_value)
                tags = " ".join(note["tags"])
                fields_values.append(tags)
                writer.writerow(fields_values)
                count += 1

        log_fn(f"  ✅ {count} cards exported")
        return count
    except Exception as e:
        log_fn(f"  ❌ Write error: {e}")
        return 0


# ──────────────────────────────────────────────
# GUI Application
# ──────────────────────────────────────────────

class AnkiCompanionApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("600x520")
        self.root.minsize(500, 450)
        self.root.resizable(True, True)

        # Apply a modern theme
        style = ttk.Style()
        available_themes = style.theme_names()
        for preferred in ("clam", "vista", "xpnative", "aqua"):
            if preferred in available_themes:
                style.theme_use(preferred)
                break

        # Configure custom styles
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), padding=10)
        style.configure("Action.TButton", font=("Segoe UI", 11), padding=(16, 8))
        style.configure("Small.TButton", font=("Segoe UI", 9), padding=(8, 4))

        self.deck_vars = []  # list of (deck_name, BooleanVar)
        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        # ── Title ──
        title = ttk.Label(self.root, text="🎴 Anki Companion", style="Title.TLabel")
        title.pack(pady=(10, 5))

        # ── Export button ──
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=5)
        self.export_btn = ttk.Button(
            btn_frame, text="Export Decks & Media…",
            style="Action.TButton", command=self._on_export_click
        )
        self.export_btn.pack()

        # ── Separator ──
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # ── Output log ──
        log_label = ttk.Label(self.root, text="Output:", font=("Segoe UI", 10))
        log_label.pack(anchor="w", padx=20)

        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(2, 10))

        self.log_text = tk.Text(
            log_frame, wrap="word", font=("Consolas", 10),
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
            relief="flat", borderwidth=0, state="disabled", height=10
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._log("Welcome to Anki Companion!")
        self._log("Make sure Anki is running with AnkiConnect enabled.")

    def _log(self, message):
        """Append a message to the output log (thread-safe)."""
        def _append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)

    def _set_running(self, running):
        self.is_running = running
        state = "disabled" if running else "normal"
        self.root.after(0, lambda: self.export_btn.configure(state=state))

    # ── Export Flow ──

    def _on_export_click(self):
        """Fetch decks from Anki, then show selector dialog."""
        self._log("\n🔄 Fetching decks from Anki…")
        self._set_running(True)

        def _fetch():
            try:
                decks = fetch_deck_names()
                self.root.after(0, lambda: self._show_deck_selector(decks))
            except Exception as e:
                self._log(f"❌ Could not connect to AnkiConnect: {e}")
                self._log("Make sure Anki is running and AnkiConnect is installed.")
                self._set_running(False)

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_deck_selector(self, decks):
        """Show a top-level dialog for deck selection."""
        self._set_running(False)

        if not decks:
            self._log("⚠️ No decks found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Select decks to export")
        dialog.geometry("450x400")
        dialog.minsize(350, 300)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Select decks to export:",
                  font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))

        # ── Scrollable checkbox list ──
        canvas_frame = ttk.Frame(dialog)
        canvas_frame.pack(fill="both", expand=True, padx=15, pady=5)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        inner_frame = ttk.Frame(canvas)

        inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        deck_vars = []
        for deck in decks:
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(inner_frame, text=deck, variable=var)
            cb.pack(anchor="w", padx=5, pady=1)
            deck_vars.append((deck, var))

        # ── Buttons ──
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=15, pady=10)

        def select_all():
            for _, v in deck_vars:
                v.set(True)

        def deselect_all():
            for _, v in deck_vars:
                v.set(False)

        ttk.Button(btn_frame, text="Select All", style="Small.TButton",
                   command=select_all).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Deselect All", style="Small.TButton",
                   command=deselect_all).pack(side="left", padx=2)

        ttk.Button(btn_frame, text="Cancel",
                   command=dialog.destroy).pack(side="right", padx=2)

        def on_export():
            selected = [name for name, var in deck_vars if var.get()]
            dialog.destroy()
            if selected:
                self._pick_folder_and_export(selected)
            else:
                self._log("⚠️ No decks selected.")

        export_btn = ttk.Button(btn_frame, text="Export", command=on_export)
        export_btn.pack(side="right", padx=2)

    def _pick_folder_and_export(self, selected_decks):
        """Ask user for destination folder, then run export."""
        dest = filedialog.askdirectory(
            title="Choose export destination folder",
            mustexist=True
        )
        if not dest:
            self._log("Export cancelled.")
            return

        self._log(f"\n📁 Exporting to: {dest}")
        self._set_running(True)

        def _do_export():
            output_dir = os.path.join(dest, "decks")
            media_dir = os.path.join(dest, "media")
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(media_dir, exist_ok=True)

            self._log(f"Exporting {len(selected_decks)} deck(s)…\n")
            total = 0
            for deck in selected_decks:
                total += export_deck(deck, output_dir, media_dir, log_fn=self._log)

            self._log(f"\n✅ DONE: {total} cards exported to {dest}")
            self._set_running(False)

        threading.Thread(target=_do_export, daemon=True).start()


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    root = tk.Tk()

    # Center window on screen
    root.update_idletasks()
    w, h = 600, 520
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    app = AnkiCompanionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
