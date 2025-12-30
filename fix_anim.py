import os
import shutil
import re
import subprocess
import requests
import zipfile
import struct
import sys
import time

# --- CONFIG ---
CREDIT = "@Huuuft"
TOOLS_ZIP_URL = "https://github.com/yasaao/TOOLS_CS1.6/raw/main/@huuuft%E2%80%94tools.zip"
TOOLS = ["mdldec.exe", "studiomdl.exe"]

# Folder Kerja (Lokal Windows)
BASE_DIR = os.getcwd()
DIRS = {
    "ref": os.path.join(BASE_DIR, "temp_ref"),
    "skin": os.path.join(BASE_DIR, "temp_skin"),
    "tools": os.path.join(BASE_DIR, "bin")
}

def log(msg, type="INFO"):
    prefixes = {"INFO": "[*]", "PROC": "[...]", "DONE": "[OK]", "WARN": "[!]", "FAIL": "[X]", "SYS": "[#]", "DNA": "[🧬]"}
    print(f"{prefixes.get(type, '[?]')} {msg}")

def setup_dirs():
    for d in DIRS.values():
        if not os.path.exists(d): os.makedirs(d)

def download_tools():
    if all(os.path.exists(os.path.join(DIRS['tools'], t)) for t in TOOLS): return
    log("Downloading Engine...", "SYS")
    try:
        r = requests.get(TOOLS_ZIP_URL)
        zip_path = os.path.join(DIRS['tools'], "tools.zip")
        with open(zip_path, 'wb') as f: f.write(r.content)
        with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(DIRS['tools'])
        for f in os.listdir(DIRS['tools']):
            low = f.lower(); src = os.path.join(DIRS['tools'], f)
            if "mdldec" in low and f != "mdldec.exe": shutil.move(src, os.path.join(DIRS['tools'], "mdldec.exe"))
            if "studiomdl" in low and f != "studiomdl.exe": shutil.move(src, os.path.join(DIRS['tools'], "studiomdl.exe"))
        log("Engine Ready.", "DONE")
    except Exception as e:
        log(f"Download Error: {e}", "FAIL"); input("Enter to exit..."); sys.exit()

def extract_texture_flags(mdl_path):
    info = []
    try:
        with open(mdl_path, "rb") as f:
            f.seek(4)
            if struct.unpack('<i', f.read(4))[0] != 10: return []
            f.seek(180); num = struct.unpack('<i', f.read(4))[0]; idx = struct.unpack('<i', f.read(4))[0]
            f.seek(idx)
            for _ in range(num):
                name = f.read(64).split(b'\0')[0].decode('utf-8', 'ignore'); flags = struct.unpack('<i', f.read(4))[0]; f.seek(12, 1)
                if flags > 0: info.append({"name": name, "flags": flags})
    except: pass
    return info

def gen_tex_qc(data):
    qc = "\n// [TEXTURE RESTORE]\n"
    for t in data:
        f = t['flags']; m = ""
        if f & 2: m = "chrome"
        elif f & 32: m = "additive"
        elif f & 64: m = "masked"
        elif f & 4: m = "fullbright"
        elif f & 1: m = "flatshade"
        if m: qc += f'$texrendermode "{t["name"]}" "{m}"\n'
    return qc

def get_anim_cat(n, c=""):
    n = n.lower(); c = c.lower()
    if "act_vm_reload" in c or any(x in n for x in ["reload", "insert", "after"]): return "reload"
    if "act_vm_draw" in c or any(x in n for x in ["draw", "deploy"]): return "draw"
    if "act_vm_shoot" in c or any(x in n for x in ["shoot", "fire", "attack"]): return "shoot"
    if "act_vm_idle" in c or any(x in n for x in ["idle", "wait", "stand"]): return "idle"
    if "inspect" in n: return "inspect"
    return "idle_watermark"

def sanitize(c): return re.sub(r'"[a-zA-Z]:\\[^"]*\\([^"\\]+\.smd)"', r'"\1"', c, flags=re.I)

def parse_qc(p):
    if not os.path.exists(p): return [], ""
    with open(p, "r", encoding="latin-1") as f: c = f.read()
    c = sanitize(c); seqs = []
    for m in re.finditer(r'(\$sequence\s+"([^"]+)"(.+?)(?=\$sequence|\Z))', c, re.DOTALL | re.MULTILINE):
        seqs.append({"name": m.group(2), "type": get_anim_cat(m.group(2), m.group(1).strip()), "code": m.group(1).strip()})
    return seqs, c

def copy_smds(qc, src, dst):
    for s in re.findall(r'[\w\-]+\.smd', qc, re.IGNORECASE):
        if os.path.exists(os.path.join(src, s)): shutil.copy(os.path.join(src, s), os.path.join(dst, s))

def run():
    os.system("cls" if os.name == 'nt' else "clear")
    print(f"=== {CREDIT} MDL FIXER (PC VERSION) ===")
    setup_dirs(); download_tools()
    
    print("\n[PETUNJUK] Pastikan file Ref & Skin ada di folder yang sama dengan exe ini.")
    files = [f for f in os.listdir('.') if f.endswith('.mdl')]
    if len(files) < 2:
        log("Minimal ada 2 file .mdl di folder ini!", "FAIL"); input("Enter..."); return

    print("-" * 30)
    for i, f in enumerate(files): print(f" [{i+1}] {f}")
    print("-" * 30)

    try:
        idx_ref = int(input(">> Pilih Nomor REFERENCE (Ori): ")) - 1
        idx_skin = int(input(">> Pilih Nomor SKIN (Mod): ")) - 1
        ref, skin = files[idx_ref], files[idx_skin]
    except: log("Input Error", "FAIL"); input("Enter..."); return

    log(f"Target: {skin}", "PROC")
    for d in [DIRS['ref'], DIRS['skin']]:
        if os.path.exists(d): shutil.rmtree(d)
        os.makedirs(d)
    for t in TOOLS: shutil.copy(os.path.join(DIRS['tools'], t), DIRS['ref']); shutil.copy(os.path.join(DIRS['tools'], t), DIRS['skin'])
    
    dna = gen_tex_qc(extract_texture_flags(skin))
    
    shutil.copy(ref, os.path.join(DIRS['ref'], "ref.mdl")); subprocess.run("mdldec.exe ref.mdl", shell=True, cwd=DIRS['ref'], stdout=subprocess.DEVNULL)
    shutil.copy(skin, os.path.join(DIRS['skin'], "skin.mdl")); subprocess.run("mdldec.exe skin.mdl", shell=True, cwd=DIRS['skin'], stdout=subprocess.DEVNULL)
    r_seqs, _ = parse_qc(os.path.join(DIRS['ref'], "ref.qc")); s_seqs, s_raw = parse_qc(os.path.join(DIRS['skin'], "skin.qc"))
    
    if not r_seqs or not s_seqs: log("File Error/Protected.", "FAIL"); return
    
    stock = {k: [] for k in ["idle", "shoot", "reload", "draw", "inspect", "other", "idle_watermark"]}; master = {}
    for s in s_seqs:
        stock[s['type']].append(s)
        if s['type'] == "idle": master["idle_main"] = s
        elif s['type'] == "idle_watermark" and "idle_main" not in master: master["idle_main"] = s
        if s['type'] not in master and s['type'] not in ["idle", "idle_watermark"]: master[s['type']] = s
        
    final = f"FIXED_{skin}"; head = re.split(r'\$sequence', s_raw)[0]
    head = re.sub(r'\$modelname\s+"[^"]+"', f'$modelname "{final}"', head, flags=re.I)
    if '$modelname' not in head: head = f'$modelname "{final}"\n{head}'
    
    new_qc = head + dna + f"\n// FIX_{CREDIT}\n"; cnt = 0
    for i, r in enumerate(r_seqs):
        t = "idle" if r['type'] == "idle_watermark" else r['type']; code = ""
        if stock[t]: code = stock[t].pop(0)['code']
        elif t == "idle" and stock["idle_watermark"]: code = stock["idle_watermark"].pop(0)['code']
        elif t in master: cnt+=1; src=master[t]; nm=f"{src['name']}_d{cnt}"; code=src['code'].replace(f'"{src["name"]}"', f'"{nm}"', 1)
        elif "idle_main" in master: cnt+=1; src=master["idle_main"]; nm=f"dum_{t}_{cnt}"; code=src['code'].replace(f'"{src["name"]}"', f'"{nm}"', 1)
        else: copy_smds(r['code'], DIRS['ref'], DIRS['skin']); code=r['code']; code=code.replace("}", " fps 30 }") if "fps" not in code.lower() else code
        if code: new_qc += f"\n// Seq {i} [{t}]\n{sanitize(code)}\n"
        
    new_qc += "\n// EXTRA\n"; 
    for k in stock: 
        for s in stock[k]: new_qc += f"\n{s['code']}\n"
    with open(os.path.join(DIRS['skin'], "fixed.qc"), "w", encoding="latin-1") as f: f.write(new_qc)
    
    log("Compiling...", "PROC")
    res = subprocess.run("studiomdl.exe fixed.qc", shell=True, cwd=DIRS['skin'], capture_output=True, text=True)
    if os.path.exists(os.path.join(DIRS['skin'], final)):
        shutil.copy(os.path.join(DIRS['skin'], final), os.path.join(BASE_DIR, final))
        log(f"SUCCESS! File: {final}", "DONE")
    else:
        log("FAIL. Logs:", "FAIL"); print(res.stdout[-300:])
    input("\nTekan Enter untuk keluar...")

if __name__ == "__main__":
    run()