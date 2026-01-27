import os
import shutil
import subprocess
import tkinter as tk
from tkinter import PhotoImage, ttk, messagebox, filedialog
from PIL import Image, ImageTk
import json
import webbrowser
import platform

# === Paths ===
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "source_pack")
OVL = os.path.join(ROOT, "overlays")
REPL = os.path.join(ROOT, "replacements")

os.makedirs(OVL, exist_ok=True)
os.makedirs(REPL, exist_ok=True)

# Make replacement subfolders
for mode in ["Dark mode", "OLED mode"]:
    os.makedirs(os.path.join(REPL, mode), exist_ok=True)

if not os.path.exists(SRC):
    raise FileNotFoundError("source_pack folder not found")

# === GUI ===
root = tk.Tk()
root.title("Minecraft Pack Updater")
root.geometry("1300x700")
root.minsize(1300, 700)

# === Icons ===
ICON_PATH = os.path.join(ROOT, "icons")
FAVICON_PATH = PhotoImage(file=os.path.join(os.path.dirname(__file__), "Logo.png"))
root.iconphoto(False, FAVICON_PATH)

def load_icon(name):
    path = os.path.join(ICON_PATH, name)
    if os.path.exists(path):
        return ImageTk.PhotoImage(Image.open(path))
    return None

icons = {
    "save": load_icon("save.png"),
    "open": load_icon("open.png"),
    "upload": load_icon("upload.png"),
    "play": load_icon("play.png"),
    "check": load_icon("check.png"),
    "trash": load_icon("trash.png"),
    "editor": load_icon("editor.png"),
    "explorer": load_icon("explorer.png"),
    "refresh": load_icon("refresh.png"),
}

# === Button style for left-aligned icons + text ===
style = ttk.Style()
style.configure("Left.TButton", padding=(5, 2), anchor="w")  # left-aligned content

# --- Tree ---
tree_frame = ttk.Frame(root, width=550)
tree_frame.pack(side="left", fill="y", padx=10, pady=10)

tree = ttk.Treeview(tree_frame, columns=("value",), show="tree headings")
tree.heading("#0", text="File")
tree.heading("value", text="Overlay/Replacement")
tree.column("#0", width=500)
tree.column("value", width=150, anchor="center")
tree.pack(fill="both", expand=True)

mapping = {}
show_all_files = tk.BooleanVar(value=False)

# --- Populate tree ---
def populate_tree():
    tree.delete(*tree.get_children())
    mapping.clear()
    _populate_tree("", SRC)

def _populate_tree(parent, path):
    for item in sorted(os.listdir(path)):
        abs_path = os.path.join(path, item)
        rel = os.path.relpath(abs_path, SRC).replace("\\", "/")
        if os.path.isdir(abs_path):
            node = tree.insert(parent, "end", text=item, open=True)
            _populate_tree(node, abs_path)
        else:
            is_png = item.lower().endswith(".png")
            if not is_png and not show_all_files.get():
                continue
            val = "" if is_png else ""
            tree.insert(parent, "end", text=item, values=(val,))
            mapping[rel] = {"type": "png" if is_png else "file", "value": None}

populate_tree()

# --- Right controls ---
right = ttk.Frame(root)
right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

top = ttk.Frame(right)
top.pack(fill="x")

left_controls = ttk.Frame(top)
left_controls.pack(side="left", fill="x", expand=True)

right_buttons = ttk.Frame(top)
right_buttons.pack(side="right")

selected_label = ttk.Label(left_controls, text="Selected: None")
selected_label.pack(fill="x", pady=8)

# --- Toggle non-PNG visibility ---
show_files_cb = ttk.Checkbutton(
    left_controls,
    text="Show non-PNG files",
    variable=show_all_files,
    command=populate_tree
)
show_files_cb.pack(anchor="w", pady=(0, 8))

# --- Folder selector ---
folder_var = tk.StringVar()

def get_overlay_folders():
    return sorted([f for f in os.listdir(OVL) if os.path.isdir(os.path.join(OVL, f))])

folder_dropdown = ttk.Combobox(
    left_controls,
    textvariable=folder_var,
    values=get_overlay_folders(),
    state="readonly"
)
folder_dropdown.pack(fill="x", pady=5)
folder_var.set("Dark mode")

# --- Overlay/Replacement selector ---
overlay_var = tk.StringVar()
overlay_dropdown = ttk.Combobox(
    left_controls,
    textvariable=overlay_var,
    state="readonly"
)
overlay_dropdown.pack(fill="x", pady=5)

# --- Apply/Remove buttons ---
apply_remove = ttk.Frame(left_controls)
apply_remove.pack(fill="x", pady=5)

apply_button = ttk.Button(
    apply_remove,
    text="Apply to Selected",
    image=icons["check"],
    compound="left",
    style="Left.TButton"
)
apply_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

remove_button = ttk.Button(
    apply_remove,
    text="Remove from Selected",
    image=icons["trash"],
    compound="left",
    style="Left.TButton"
)
remove_button.pack(side="left", expand=True, fill="x")

# --- Right buttons ---
load_btn = ttk.Button(
    right_buttons,
    text="Load Preset",
    image=icons["open"],
    compound="left",
    style="Left.TButton"
)
load_btn.pack(fill="x", pady=5)

save_btn = ttk.Button(
    right_buttons,
    text="Save Preset",
    image=icons["save"],
    compound="left",
    style="Left.TButton"
)
save_btn.pack(fill="x", pady=5)

settings_btn = ttk.Button(
    right_buttons,
    text="Settings",
    image=icons["upload"],
    compound="left",
    style="Left.TButton"
)
settings_btn.pack(fill="x", pady=5)

done_btn = ttk.Button(
    right_buttons,
    text="Export",
    image=icons["play"],
    compound="left",
    style="Left.TButton"
)
done_btn.pack(fill="x", pady=5)

# --- Preview area ---
preview_container = ttk.Frame(right)
preview_container.pack(fill="both", expand=True, pady=10)

def refresh_preview():
    if current_selection:
        show_preview(current_selection)

# Info label (size for PNGs, lines for text)
info_label = ttk.Label(preview_container, text="")
info_label.grid(row=0, column=0, sticky="ew", pady=(0, 2))

# Canvas for PNG preview
preview_canvas = tk.Canvas(preview_container, bg="#ccc", highlightthickness=0)
preview_canvas.grid(row=1, column=0, sticky="nsew")

# Text preview for non-PNG files
text_frame = ttk.Frame(preview_container)
text_scroll = ttk.Scrollbar(text_frame)
text_scroll.pack(side="right", fill="y")
text_preview = tk.Text(
    text_frame,
    wrap="none",
    yscrollcommand=text_scroll.set,
    state="disabled"
)
text_preview.pack(fill="both", expand=True)
text_scroll.config(command=text_preview.yview)
text_frame.grid(row=1, column=0, sticky="nsew")

# Configure grid to expand preview area
preview_container.rowconfigure(1, weight=1)
preview_container.columnconfigure(0, weight=1)

# --- Preview action buttons ---
preview_buttons = ttk.Frame(preview_container)
preview_buttons.grid(row=2, column=0, sticky="w", pady=(6, 0))

refresh_btn = ttk.Button(
    preview_buttons,
    text="Refresh Preview",
    image=icons["refresh"],
    compound="left",
    style="Left.TButton"
)
refresh_btn.pack(side="left", padx=(0, 6))

refresh_btn.config(command=refresh_preview)


open_external_btn = ttk.Button(
    preview_buttons,
    text="Open in external editor",
    image=icons["editor"],
    compound="left",
    style="Left.TButton"
)
open_external_btn.pack(side="left", padx=(0, 6))

open_explorer_btn = ttk.Button(
    preview_buttons,
    text="View in Explorer",
    image=icons["explorer"],
    compound="left",
    style="Left.TButton"
)
open_explorer_btn.pack(side="left")

# Initially hide buttons until selection
open_external_btn.pack_forget()
open_explorer_btn.pack_forget()
refresh_btn.pack_forget()

preview_image = None
current_selection = None

# === Helpers ===
def get_rel_path(node):
    parts = []
    while node:
        parts.append(tree.item(node)["text"])
        node = tree.parent(node)
    return "/".join(reversed(parts))

def prioritize_matching_overlay(file_list, target_name):
    files = sorted(file_list)
    if target_name in files:
        files.remove(target_name)
        files.insert(0, target_name)
    return files

def draw_checkered_background(pil_img):
    w, h = pil_img.size
    tile_size = 8
    bg = Image.new("RGBA", pil_img.size)
    color1 = (200, 200, 200, 255)
    color2 = (150, 150, 150, 255)
    for y in range(0, h, tile_size):
        for x in range(0, w, tile_size):
            color = color1 if (x // tile_size + y // tile_size) % 2 == 0 else color2
            for dy in range(tile_size):
                for dx in range(tile_size):
                    if x + dx < w and y + dy < h:
                        bg.putpixel((x + dx, y + dy), color)
    bg.alpha_composite(pil_img)
    return bg

def show_image(pil_img):
    global preview_image
    if pil_img is None:
        preview_canvas.delete("all")
        info_label.grid_remove()
        return

    img_with_bg = draw_checkered_background(pil_img)
    preview_image = ImageTk.PhotoImage(img_with_bg)
    preview_canvas.delete("all")
    preview_canvas.create_image(0, 0, image=preview_image, anchor="nw")
    preview_canvas.grid()
    text_frame.grid_remove()
    info_label.config(text=f"Size: {pil_img.width} x {pil_img.height} px")
    info_label.grid()

def show_text(content):
    preview_canvas.grid_remove()
    text_frame.grid()
    text_preview.config(state="normal")
    text_preview.delete("1.0", "end")
    text_preview.insert("1.0", content)
    text_preview.config(state="disabled")
    lines = content.count("\n") + 1 if content else 0
    info_label.config(text=f"Lines: {lines}")
    info_label.grid()

def show_preview(rel, temp_value=None):
    global preview_image
    if rel not in mapping:
        preview_canvas.delete("all")
        info_label.grid_remove()
        return

    entry = mapping[rel]
    base_path = os.path.join(SRC, rel.replace("/", os.sep))

    if entry["type"] == "png":
        img = Image.open(base_path).convert("RGBA")
        val = temp_value if temp_value is not None else entry["value"]
        if val:
            folder = folder_var.get()
            overlay_path = os.path.join(OVL, folder, val)
            if os.path.exists(overlay_path):
                overlay_img = Image.open(overlay_path).convert("RGBA")
                img.alpha_composite(overlay_img)
        show_image(img)
    else:
        folder = folder_var.get()
        val = temp_value if temp_value is not None else entry["value"]
        path = base_path
        if val:
            repl_path = os.path.join(REPL, folder, val)
            if os.path.exists(repl_path):
                path = repl_path
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = "(Binary or unreadable file)"
        show_text(content)

# === Tree selection ===
def on_select(event):
    global current_selection
    sel = tree.selection()
    if not sel:
        return
    rel = get_rel_path(sel[0])
    current_selection = rel
    selected_label.config(text=f"Selected: {rel}")

    # Determine overlay/replacement files
    if rel in mapping:
        entry = mapping[rel]
        folder = folder_var.get()
        filename = os.path.basename(rel)
        if entry["type"] == "png":
            files = os.listdir(os.path.join(OVL, folder)) if folder else []
        else:
            files = os.listdir(os.path.join(REPL, folder)) if folder else []
        overlay_dropdown["values"] = prioritize_matching_overlay(files, filename)
        overlay_var.set(entry["value"] or "")
        show_preview(rel)
    else:
        overlay_dropdown["values"] = []
        overlay_var.set("")
        preview_canvas.delete("all")
        info_label.grid_remove()

    # --- Handle preview buttons visibility ---
    open_external_btn.pack_forget()
    open_explorer_btn.pack_forget()
    refresh_btn.pack_forget()
    if rel not in mapping:
        return
    if mapping[rel]["type"] in ("png", "file"):
        refresh_btn.pack(side="left", padx=(0, 6))
        open_external_btn.pack(side="left", padx=(0, 6))
    open_explorer_btn.pack(side="left")
    

tree.bind("<<TreeviewSelect>>", on_select)

def overlay_preview(event):
    if current_selection:
        show_preview(current_selection, temp_value=overlay_var.get() or None)

overlay_dropdown.bind("<<ComboboxSelected>>", overlay_preview)

def folder_changed(event):
    if not current_selection:
        return
    rel = current_selection
    if rel not in mapping:
        return
    entry = mapping[rel]
    folder = folder_var.get()
    filename = os.path.basename(rel)
    if entry["type"] == "png":
        files = os.listdir(os.path.join(OVL, folder)) if folder else []
    else:
        files = os.listdir(os.path.join(REPL, folder)) if folder else []
    overlay_dropdown["values"] = prioritize_matching_overlay(files, filename)
    if entry["value"] not in overlay_dropdown["values"]:
        overlay_var.set("")
    else:
        overlay_var.set(entry["value"])
    show_preview(rel)

folder_dropdown.bind("<<ComboboxSelected>>", folder_changed)

# === Apply/Remove helpers ===
def apply_to_children(node, val):
    for c in tree.get_children(node):
        rel = get_rel_path(c)
        if rel in mapping:
            mapping[rel]["value"] = val
            tree.set(c, "value", val or "")
        else:
            apply_to_children(c, val)

def apply_value():
    val = overlay_var.get() or None
    sel = tree.selection()
    if not sel:
        return
    for node in sel:
        rel = get_rel_path(node)
        if rel in mapping:
            mapping[rel]["value"] = val
            tree.set(node, "value", val or "")
            show_preview(rel)
        else:
            apply_to_children(node, val)

def remove_value():
    sel = tree.selection()
    if not sel:
        return
    for node in sel:
        rel = get_rel_path(node)
        if rel in mapping:
            mapping[rel]["value"] = None
            tree.set(node, "value", "")
        else:
            apply_to_children(node, None)
    overlay_var.set("")
    if sel[0] in mapping:
        show_preview(get_rel_path(sel[0]))
    else:
        preview_canvas.delete("all")
        info_label.grid_remove()

apply_button.config(command=apply_value)
remove_button.config(command=remove_value)

# === Presets ===
def save_preset():
    path = filedialog.asksaveasfilename(defaultextension=".json")
    if path:
        json.dump(mapping, open(path, "w"), indent=4)
        messagebox.showinfo("Preset Saved", f"Preset saved to:\n{path}")

def load_preset():
    path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if not path:
        return
    data = json.load(open(path))
    populate_tree()
    for rel in mapping:
        if rel in data:
            mapping[rel]["value"] = data[rel].get("value")
    for node in tree.get_children(""):
        refresh_tree(node)
    messagebox.showinfo("Preset Loaded", f"Preset loaded from:\n{path}")

def refresh_tree(node):
    rel = get_rel_path(node)
    if rel in mapping:
        tree.set(node, "value", mapping[rel]["value"] or "")
    for c in tree.get_children(node):
        refresh_tree(c)

load_btn.config(command=load_preset)
save_btn.config(command=save_preset)

def open_settings():
    # Simple placeholder popup for now
    popup = tk.Toplevel(root)
    popup.title("Settings")
    popup.geometry("400x300")
    popup.iconphoto(False, FAVICON_PATH)
    ttk.Label(popup, text="Coming Soon!").pack(padx=20, pady=20)

settings_btn.config(command=open_settings)

# === Process/export pack ===
def process_pack():
    folder = folder_var.get()
    out_dir = os.path.join(ROOT, f"{folder} output" if folder else "output_pack")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(SRC, out_dir)
    for rel, entry in mapping.items():
        if not entry["value"]:
            continue
        src_path = os.path.join(out_dir, rel.replace("/", os.sep))
        if entry["type"] == "png":
            overlay_path = os.path.join(OVL, folder, entry["value"])
            subprocess.run(
                ["magick", src_path, overlay_path, "-compose", "over", "-composite", src_path],
                check=True
            )
        else:
            repl_path = os.path.join(REPL, folder, entry["value"])
            shutil.copy(repl_path, src_path)
    messagebox.showinfo("Done", f"Output pack created:\n{os.path.basename(out_dir)}")

done_btn.config(command=process_pack)

# === External/Open in Explorer actions ===
def open_in_editor():
    if not current_selection:
        return

    path = os.path.join(SRC, current_selection.replace("/", os.sep))

    if not os.path.exists(path):
        messagebox.showerror("Error", f"Path does not exist:\n{path}")
        return

    try:
        if os.path.isdir(path):
            # For folders, open in Explorer/Finder
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            # For files
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Error", f"Could not open file/folder:\n{e}")

def open_in_explorer():
    if current_selection:
        path = os.path.join(SRC, current_selection.replace("/", os.sep))
        if os.path.isdir(path):
            webbrowser.open(path)
        else:
            folder = os.path.dirname(path)
            webbrowser.open(folder)

open_external_btn.config(command=open_in_editor)
open_explorer_btn.config(command=open_in_explorer)

root.mainloop()
