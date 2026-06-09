import os
import subprocess
import shutil
import threading
import platform
import argparse
import sys

# --- Встроенные движки ---
try:
    import pypff
except ImportError:
    pypff = None

try:
    from tnefparse import TNEF
except ImportError:
    TNEF = None

# --- Общая логика (без GUI) ---
def get_app_dir():
    # Стабильная папка рядом с программой (учитывает сборку PyInstaller).
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# Сюда складывается скачанный движок (readpst.exe + DLL), чтобы не сорить в корень.
ENGINE_DIR = os.path.join(get_app_dir(), "rpst")

def get_engine_info():
    is_win = platform.system() == "Windows"
    exe = "readpst.exe" if is_win else "readpst"
    # 1. Локальный движок в папке rpst/ (скачанный кнопкой Download Engine).
    local_exe = os.path.join(ENGINE_DIR, exe)
    if os.path.exists(local_exe): return "readpst", os.path.abspath(local_exe)
    # 2. Системный readpst в PATH.
    try:
        cmd = "where readpst" if is_win else "which readpst"
        if subprocess.run(cmd, shell=True, capture_output=True).returncode == 0: return "readpst", exe
    except: pass
    if pypff: return "python", None
    return "none", None

def get_pst_files(source):
    source = os.path.abspath(source)
    files = []
    if os.path.isfile(source) and source.lower().endswith(".pst"): 
        files.append(source)
    elif os.path.isdir(source):
        for r, d, fnames in os.walk(source):
            for f in fnames:
                if f.lower().endswith(".pst"): files.append(os.path.join(r, f))
    return files

def organize_mbox(temp_dir, final_dst, pst_base):
    src_root = os.path.join(temp_dir, f".{pst_base}.directory")
    if not os.path.exists(src_root):
        items = [d for d in os.listdir(temp_dir) if d.endswith(".directory")]
        src_root = os.path.join(temp_dir, items[0]) if items else None
    if not src_root: return ""
    
    target_base = os.path.join(final_dst, pst_base)
    if not os.path.exists(target_base): open(target_base, "w").close()
    os.makedirs(target_base + ".sbd", exist_ok=True)

    def move_rec(src, target_p):
        if not os.path.isdir(src): return
        for item in os.listdir(src):
            ipath = os.path.join(src, item)
            if item.endswith(".mbox"):
                fname = item[:-5]; dfile = os.path.join(target_p + ".sbd", fname)
                os.makedirs(os.path.dirname(dfile), exist_ok=True); shutil.copy2(ipath, dfile)
                sdir = os.path.join(src, f".{fname}.directory")
                if os.path.isdir(sdir): os.makedirs(dfile + ".sbd", exist_ok=True); move_rec(sdir, dfile)
            elif item.endswith(".directory") and item.startswith("."):
                fname = item[1:-10]; dfile = os.path.join(target_p + ".sbd", fname)
                if not os.path.exists(dfile): os.makedirs(os.path.dirname(dfile), exist_ok=True); open(dfile, "w").close()
                os.makedirs(dfile + ".sbd", exist_ok=True); move_rec(ipath, dfile)
    
    move_rec(src_root, target_base)
    return target_base

def extract_tnef_data(m, out):
    if not TNEF: return
    for i in range(m.get_number_of_attachments()):
        a = m.get_attachment(i)
        if (a.get_name() or "").lower() == "winmail.dat":
            d = a.get_data()
            if d:
                os.makedirs(out, exist_ok=True)
                t = TNEF(d)
                for ta in t.attachments:
                    with open(os.path.join(out, ta.name.decode("utf-8", "replace")), "wb") as f: f.write(ta.data)

# --- CLI Application (Не использует Tkinter) ---
class CLIApp:
    def __init__(self, source, dest, recover, extract_tnef):
        self.source = source
        self.dest = dest
        self.recover = recover
        self.extract_tnef = extract_tnef
        self.engine_mode, self.exe_path = get_engine_info()
        
        if self.engine_mode == "none":
            print("ERROR: Neither readpst nor pypff found.")
            sys.exit(1)
        elif self.engine_mode == "python":
            print("WARNING: readpst not found. Using built-in Python engine (slower).")

    def run(self):
        files = get_pst_files(self.source)
        if not files:
            print("No PST files found.")
            return

        total = len(files)
        for i, path in enumerate(files):
            name = os.path.splitext(os.path.basename(path))[0]
            print(f"[{i+1}/{total}] Processing: {name}...")
            
            if self.engine_mode == "readpst":
                self.run_readpst(path, self.dest, name)
            else:
                self.run_python(path, self.dest, name)

        print(">>> DONE!")

    def run_readpst(self, pst, dst, name):
        temp = os.path.join(dst, f"_temp_{name}")
        os.makedirs(temp, exist_ok=True)
        cmd = [self.exe_path, "-u", "-M", "-r", "-o", temp]
        if self.recover: cmd.append("-k")
        cmd.append(pst)
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=(platform.system()=="Windows"), encoding="utf-8", errors="replace")
            for line in p.stdout: print(f"  {line.strip()}")
            p.wait()
            if p.returncode == 0:
                target = organize_mbox(temp, dst, name)
                if self.extract_tnef: self.scan_tnef_recursive(target)
                shutil.rmtree(temp)
        except Exception as e: print(f"readpst error: {e}")

    def run_python(self, pst_path, dst, name):
        try:
            p = pypff.file()
            p.open(os.path.abspath(pst_path))
            root = os.path.join(dst, name)
            if not os.path.exists(root): open(root, "w").close()
            os.makedirs(root + ".sbd", exist_ok=True)
            self.traverse(p.get_root_folder(), root)
            p.close()
        except Exception as e: print(f"Python Engine Error: {e}")

    def traverse(self, folder, prefix):
        fname = folder.get_name() or "Mailbox"
        if fname == "IPM_SUBTREE": fname = "Mailbox"
        mbox = os.path.join(prefix + ".sbd", fname)
        os.makedirs(os.path.dirname(mbox), exist_ok=True)
        
        count = folder.get_number_of_sub_messages()
        if count > 0:
            print(f"    Folder: {fname} ({count} messages)")
            with open(mbox, "a", encoding="utf-8", errors="replace") as f:
                for i in range(count):
                    m = folder.get_sub_message(i)
                    subj = m.get_subject() or "(No Subject)"
                    send = m.get_sender_name() or "Unknown"
                    date = m.get_delivery_time() or ""
                    body = m.get_plain_text_body() or m.get_html_body() or ""
                    if isinstance(body, bytes): body = body.decode("utf-8", "replace")
                    f.write(f"From {send} {date}\nSubject: {subj}\nFrom: {send}\nDate: {date}\nContent-Type: text/plain; charset=utf-8\n\n{body}\n\n")
                    if self.extract_tnef:
                        try: extract_tnef_data(m, mbox + "_attachments")
                        except: pass
        elif not os.path.exists(mbox): open(mbox, "w").close()

        for i in range(folder.get_number_of_sub_folders()):
            self.traverse(folder.get_sub_folder(i), mbox)

    def scan_tnef_recursive(self, root_path):
        for r, d, fnames in os.walk(root_path + ".sbd"):
            for f in fnames:
                if not f.endswith(".sbd"):
                    path = os.path.join(r, f)
                    try:
                        if b"winmail.dat" in open(path, "rb").read(500000):
                            print(f"  [TNEF] Found in {f}")
                    except: pass


# --- GUI Application (Загружается только если нет флага --cli) ---
def launch_gui(initial_src, initial_dst):
    import tkinter as tk
    from tkinter import filedialog, messagebox
    import customtkinter as ctk
    import webbrowser

    class PSTGrabberApp(ctk.CTk):
        def __init__(self, src="", dst=""):
            super().__init__()

            self.title("PST Grabber - Outlook to Thunderbird [v 0.12]")
            self.geometry("750x750")
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            
            self.engine_mode, self.exe_path = get_engine_info()
            self.is_running = False
            self.stop_requested = False
            self.current_process = None

            self.setup_ui(src, dst)

        def setup_ui(self, src, dst):
            self.grid_columnconfigure(0, weight=1)
            
            ctk.CTkLabel(self, text="PST to Thunderbird Converter", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=20, pady=(25, 5))
            self.engine_label = ctk.CTkLabel(self, text="Engine: Detecting...", font=ctk.CTkFont(size=12))
            self.engine_label.grid(row=1, column=0, padx=20, pady=(0, 15))

            self.dep_frame = ctk.CTkFrame(self, fg_color="#442222")
            self.dep_label = ctk.CTkLabel(self.dep_frame, text="⚠️ readpst not found! Using built-in engine.", text_color="white")
            self.btn_fix = ctk.CTkButton(self.dep_frame, text="Download Engine", width=120, command=self.auto_download_engine)
            
            if self.engine_mode == "readpst":
                self.engine_label.configure(text="Engine: readpst (High Performance)", text_color="#2ecc71")
            elif self.engine_mode == "python":
                self.engine_label.configure(text="Engine: Native Python (Built-in)", text_color="#f1c40f")
                self.dep_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
                self.dep_label.pack(side="left", padx=15, pady=8)
                self.btn_fix.pack(side="right", padx=15, pady=8)
            else:
                self.engine_label.configure(text="Engine: NOT FOUND!", text_color="#e74c3c")
                self.dep_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
                self.dep_label.pack(side="left", padx=15, pady=8)
                self.btn_fix.pack(side="right", padx=15, pady=8)

            self.ctrl_frame = ctk.CTkFrame(self)
            self.ctrl_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
            self.ctrl_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(self.ctrl_frame, text="Source:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
            self.in_entry = ctk.CTkEntry(self.ctrl_frame, placeholder_text="Select PST file or folder...")
            self.in_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            if src: self.in_entry.insert(0, src)
            
            self.btn_file = ctk.CTkButton(self.ctrl_frame, text="File", width=60, command=self.browse_file)
            self.btn_file.grid(row=0, column=2, padx=5, pady=10)
            self.btn_folder = ctk.CTkButton(self.ctrl_frame, text="Folder", width=60, command=self.browse_folder)
            self.btn_folder.grid(row=0, column=3, padx=5, pady=10)

            ctk.CTkLabel(self.ctrl_frame, text="Destination:").grid(row=1, column=0, padx=15, pady=10, sticky="w")
            self.out_entry = ctk.CTkEntry(self.ctrl_frame, placeholder_text="Output folder...")
            self.out_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
            if dst: self.out_entry.insert(0, dst)
            
            self.btn_dest = ctk.CTkButton(self.ctrl_frame, text="Browse", width=130, command=self.browse_dest)
            self.btn_dest.grid(row=1, column=2, columnspan=2, padx=10, pady=10)

            self.opt_frame = ctk.CTkFrame(self)
            self.opt_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
            self.check_k = ctk.CTkCheckBox(self.opt_frame, text="Recover Mode (-k)")
            self.check_k.select(); self.check_k.grid(row=0, column=0, padx=20, pady=15)
            self.check_t = ctk.CTkCheckBox(self.opt_frame, text="Extract TNEF (winmail.dat)")
            self.check_t.select(); self.check_t.grid(row=0, column=1, padx=20, pady=15)

            self.pbar = ctk.CTkProgressBar(self)
            self.pbar.grid(row=5, column=0, padx=20, pady=(15, 5), sticky="ew"); self.pbar.set(0)
            self.log_box = ctk.CTkTextbox(self, height=250, font=ctk.CTkFont(family="monospace", size=12))
            self.log_box.grid(row=6, column=0, padx=20, pady=10, sticky="nsew")
            self.grid_rowconfigure(6, weight=1)

            # Action Button
            self.btn_run = ctk.CTkButton(self, text="START CONVERSION", height=45, font=ctk.CTkFont(size=16, weight="bold"), command=self.toggle_state)
            self.btn_run.grid(row=7, column=0, padx=20, pady=15, sticky="ew")

            self.foot = ctk.CTkLabel(self, text="Powered by aLex Di  [v 0.12]", font=ctk.CTkFont(size=12, underline=True), cursor="hand2")
            self.foot.grid(row=8, column=0, padx=20, pady=10)
            self.foot.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/alex-di-96/"))

        def log(self, msg):
            self.log_box.insert(tk.END, f"{msg}\n"); self.log_box.see(tk.END); print(msg)

        def auto_download_engine(self):
            import urllib.request
            import zipfile

            if platform.system() != "Windows":
                messagebox.showinfo("Linux", "On Linux, please use: sudo apt install pst-utils")
                return

            self.btn_fix.configure(state="disabled", text="Downloading...")
            self.log(">>> [AUTO-INSTALL] Downloading readpst engine from SourceForge...")
            # Direct mirror link: the plain ".../download" page returns an HTML
            # redirect (driven by JS) that urllib can't follow, so we hit a real
            # mirror that streams the zip directly.
            url = "https://master.dl.sourceforge.net/project/ezwinports/libpst-0.6.63-w32-bin.zip?viasf=1"
            zip_path = os.path.join(ENGINE_DIR, "libpst.zip")

            def download_thread():
                try:
                    os.makedirs(ENGINE_DIR, exist_ok=True)
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)

                    # Guard against mirror outages returning an HTML page instead
                    # of the archive (would otherwise blow up as BadZipFile).
                    if not zipfile.is_zipfile(zip_path):
                        os.remove(zip_path)
                        raise RuntimeError("Download did not return a valid ZIP (mirror may be down). Please download manually from SourceForge.")

                    self.after(0, lambda: self.log(">>> Download complete. Extracting..."))

                    # exe и DLL кладём плоско в rpst/ (DLL должны лежать рядом с exe).
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        for file_info in zip_ref.infolist():
                            if file_info.filename.startswith('bin/') and (file_info.filename.endswith('.exe') or file_info.filename.endswith('.dll')):
                                extracted_path = zip_ref.extract(file_info, path=ENGINE_DIR)
                                target_path = os.path.join(ENGINE_DIR, os.path.basename(file_info.filename))
                                if os.path.abspath(extracted_path) != os.path.abspath(target_path):
                                    if os.path.exists(target_path):
                                        os.remove(target_path)
                                    os.rename(extracted_path, target_path)

                    leftover_bin = os.path.join(ENGINE_DIR, "bin")
                    if os.path.isdir(leftover_bin): shutil.rmtree(leftover_bin, ignore_errors=True)
                    os.remove(zip_path)
                    
                    self.after(0, lambda: self.log(">>> Engine installed successfully!"))
                    self.after(0, lambda: messagebox.showinfo("Success", "Engine downloaded! Please restart the application."))
                except Exception as e:
                    self.after(0, lambda m=str(e): self.log(f"DOWNLOAD ERROR: {m}"))
                    self.after(0, lambda: self.btn_fix.configure(state="normal", text="Download Engine"))

            threading.Thread(target=download_thread, daemon=True).start()

        def browse_file(self):
            f = filedialog.askopenfilename(filetypes=[("Outlook PST", "*.pst")])
            if f: self.in_entry.delete(0, tk.END); self.in_entry.insert(0, os.path.normpath(f))

        def browse_folder(self):
            d = filedialog.askdirectory()
            if d: self.in_entry.delete(0, tk.END); self.in_entry.insert(0, os.path.normpath(d))

        def browse_dest(self):
            d = filedialog.askdirectory()
            if d: self.out_entry.delete(0, tk.END); self.out_entry.insert(0, os.path.normpath(d))

        def set_ui_state(self, state):
            self.btn_file.configure(state=state)
            self.btn_folder.configure(state=state)
            self.btn_dest.configure(state=state)
            self.in_entry.configure(state=state)
            self.out_entry.configure(state=state)
            self.check_k.configure(state=state)
            self.check_t.configure(state=state)

        def toggle_state(self):
            if self.is_running:
                self.stop_requested = True
                self.log(">>> ОСТАНОВКА ПРОЦЕССА...")
                self.btn_run.configure(state="disabled", text="STOPPING...")
                if self.current_process:
                    try: self.current_process.terminate()
                    except: pass
            else:
                self.start()

        def start(self):
            src, dst = self.in_entry.get(), self.out_entry.get()
            if not src or not dst: return messagebox.showerror("Error", "Select source and destination.")
            if self.engine_mode == "none": return messagebox.showerror("Error", "Engine not found!")
            
            self.is_running = True
            self.stop_requested = False
            self.set_ui_state("disabled")
            self.btn_run.configure(text="STOP CONVERSION", fg_color="#e74c3c", hover_color="#c0392b")
            self.log_box.delete("1.0", tk.END); self.pbar.set(0)
            threading.Thread(target=self.run, args=(src, dst), daemon=True).start()

        def run(self, source, dest):
            try:
                files = get_pst_files(source)
                if not files: return self.after(0, lambda: self.log("No PST files found."))

                total = len(files)
                for i, path in enumerate(files):
                    if self.stop_requested: break
                    name = os.path.splitext(os.path.basename(path))[0]
                    self.after(0, lambda n=name: self.log(f"[{i+1}/{total}] Processing: {n}..."))
                    
                    if self.engine_mode == "readpst":
                        self.run_readpst(path, dest, name)
                    else:
                        self.run_python(path, dest, name)
                    
                    if not self.stop_requested:
                        self.after(0, lambda v=(i+1)/total: self.pbar.set(v))

                if self.stop_requested:
                    self.after(0, lambda: self.log(">>> ПРОЦЕСС ПРЕРВАН ПОЛЬЗОВАТЕЛЕМ!"))
                else:
                    self.after(0, lambda: self.log(">>> DONE!"))
                    self.after(0, lambda: messagebox.showinfo("Success", "Conversion finished!"))
            except Exception as e:
                self.after(0, lambda m=str(e): self.log(f"CRITICAL ERROR: {m}"))
            finally:
                self.after(0, lambda: self.reset_ui())

        def reset_ui(self):
            self.is_running = False
            self.set_ui_state("normal")
            self.btn_run.configure(state="normal", text="START CONVERSION", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"])
            self.current_process = None

        def run_readpst(self, pst, dst, name):
            temp = os.path.join(dst, f"_temp_{name}")
            os.makedirs(temp, exist_ok=True)
            cmd = [self.exe_path, "-u", "-M", "-r", "-o", temp]
            if self.check_k.get(): cmd.append("-k")
            cmd.append(pst)
            try:
                self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=(platform.system()=="Windows"), encoding="utf-8", errors="replace")
                for line in self.current_process.stdout:
                    if self.stop_requested:
                        self.current_process.terminate()
                        break
                    self.after(0, lambda l=line.strip(): self.log(f"  {l}"))
                self.current_process.wait()
                self.current_process = None
                if not self.stop_requested and os.path.exists(temp):
                    target = organize_mbox(temp, dst, name)
                    if self.check_t.get(): self.scan_tnef_recursive(target)
                    shutil.rmtree(temp)
            except Exception as e: self.log(f"readpst error: {e}")

        def run_python(self, pst_path, dst, name):
            try:
                p = pypff.file()
                p.open(os.path.abspath(pst_path))
                root = os.path.join(dst, name)
                if not os.path.exists(root): open(root, "w").close()
                os.makedirs(root + ".sbd", exist_ok=True)
                self.traverse(p.get_root_folder(), root)
                p.close()
            except Exception as e: self.log(f"Python Engine Error: {e}")

        def traverse(self, folder, prefix):
            if self.stop_requested: return
            fname = folder.get_name() or "Mailbox"
            if fname == "IPM_SUBTREE": fname = "Mailbox"
            mbox = os.path.join(prefix + ".sbd", fname)
            os.makedirs(os.path.dirname(mbox), exist_ok=True)
            
            count = folder.get_number_of_sub_messages()
            if count > 0:
                self.after(0, lambda n=fname, c=count: self.log(f"    Folder: {n} ({c} messages)"))
                with open(mbox, "a", encoding="utf-8", errors="replace") as f:
                    for i in range(count):
                        if self.stop_requested: break
                        m = folder.get_sub_message(i)
                        subj = m.get_subject() or "(No Subject)"
                        send = m.get_sender_name() or "Unknown"
                        date = m.get_delivery_time() or ""
                        body = m.get_plain_text_body() or m.get_html_body() or ""
                        if isinstance(body, bytes): body = body.decode("utf-8", "replace")
                        f.write(f"From {send} {date}\nSubject: {subj}\nFrom: {send}\nDate: {date}\nContent-Type: text/plain; charset=utf-8\n\n{body}\n\n")
                        if self.check_t.get():
                            try: extract_tnef_data(m, mbox + "_attachments")
                            except: self.after(0, lambda: self.log("      ! Skipping attachments (lib error)"))
            elif not os.path.exists(mbox): open(mbox, "w").close()

            for i in range(folder.get_number_of_sub_folders()):
                if self.stop_requested: break
                self.traverse(folder.get_sub_folder(i), mbox)

        def scan_tnef_recursive(self, root_path):
            for r, d, fnames in os.walk(root_path + ".sbd"):
                for f in fnames:
                    if self.stop_requested: break
                    if not f.endswith(".sbd"):
                        path = os.path.join(r, f)
                        try:
                            if b"winmail.dat" in open(path, "rb").read(500000):
                                self.after(0, lambda n=f: self.log(f"  [TNEF] Found in {n}"))
                        except: pass

    PSTGrabberApp(initial_src, initial_dst).mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PST to Thunderbird Converter")
    parser.add_argument("-s", "--source", help="Path to PST file or folder", default="")
    parser.add_argument("-d", "--dest", help="Destination folder for MBOX", default="")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode (No GUI)")
    parser.add_argument("--no-recover", action="store_true", help="Disable recovery mode (-k)")
    parser.add_argument("--no-tnef", action="store_true", help="Disable TNEF (winmail.dat) extraction")
    
    args = parser.parse_args()
    
    if args.cli:
        if not args.source or not args.dest:
            print("ERROR: --source and --dest are required when using --cli")
            sys.exit(1)
        print("Starting Headless CLI Mode...")
        cli = CLIApp(args.source, args.dest, not args.no_recover, not args.no_tnef)
        cli.run()
    else:
        # Launch GUI (Will pre-fill -s and -d if provided)
        launch_gui(args.source, args.dest)
