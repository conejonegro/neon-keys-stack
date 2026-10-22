#!/usr/bin/env python3
"""Interfaz web local de Neon Keys.

Uso:
    .venv/bin/python app.py
    → abre http://127.0.0.1:5050
"""

import json
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import uuid
from pathlib import Path

import mido
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
MIDI_DIR = ROOT / "midi"
OUT_DIR = ROOT / "out"
PREVIEW_DIR = OUT_DIR / ".preview"
VIDEOS_DIR = OUT_DIR / "videos"       # videos terminados
PRUEBAS_DIR = OUT_DIR / "pruebas"     # pruebas y teasers
VIDEO_DIRS = (VIDEOS_DIR, PRUEBAS_DIR)
META_FILE = OUT_DIR / "videos.json"   # descripción, hashtags y estado de publicación de cada video
IDEAS_FILE = OUT_DIR / "ideas.json"   # ideas para los próximos videos + plantilla del prompt para IA de video
PROBAR_FILE = OUT_DIR / "por-probar.json"   # skills, librerías y herramientas que queremos probar
PROBAR_TIPOS = ("skill", "libreria", "otro")
FFPROBE = shutil.which("ffprobe") or str(Path.home() / ".local" / "bin" / "ffprobe")
MIN_MONETIZABLE = 62.0               # segundos; ver docs/TIKTOK.md
ESTADOS = ("listo", "programado", "publicado")
SCRIPT = ROOT / "neon_keys.py"
PY = sys.executable

for d in (MIDI_DIR, OUT_DIR, PREVIEW_DIR, *VIDEO_DIRS):
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

jobs = {}
jobs_lock = threading.Lock()
meta_lock = threading.Lock()
durations = {}   # (nombre, mtime) → segundos
PROGRESS_RE = re.compile(r"([\d.]+)s / ([\d.]+)s")


# Tipo de video según el inicio del nombre del archivo; lo que no coincide es de piano.
VIDEO_TYPES = (("dato-", "datos"), ("rebotes-", "bolitas"), ("podcast-", "podcast"), ("caricatura-", "caricatura"))


def video_type(name):
    return next((t for prefix, t in VIDEO_TYPES if name.startswith(prefix)), "piano")


def load_meta():
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_meta(meta, path=META_FILE):
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_ideas():
    try:
        return json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"plantilla_prompt": "", "ideas": []}


def load_probar():
    try:
        return json.loads(PROBAR_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"items": []}


def video_duration(path, mtime):
    key = (path.name, mtime)
    if key not in durations:
        res = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(path)], capture_output=True, text=True)
        try:
            durations[key] = round(float(res.stdout.strip()), 1)
        except ValueError:
            durations[key] = None
    return durations[key]


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "video"


def find_video(name):
    """Ruta de un video por su nombre, esté en videos/ o en pruebas/ (los nombres no se repiten)."""
    name = secure_filename(name)
    return next((d / name for d in VIDEO_DIRS if (d / name).is_file() and name.endswith(".mp4")), None)


def unique_output(name):
    path = VIDEOS_DIR / f"{name}.mp4"
    i = 2
    while path.exists() or find_video(path.name):
        path = VIDEOS_DIR / f"{name}-{i}.mp4"
        i += 1
    return path


def midi_path(name):
    path = MIDI_DIR / secure_filename(name or "")
    if not path.is_file() or path.suffix.lower() not in (".mid", ".midi"):
        return None
    return path


def build_args(data, midi):
    args = [PY, "-u", str(SCRIPT), str(midi)]
    if data.get("titulo"):
        args += ["--titulo", str(data["titulo"])]
    if data.get("subtitulo"):
        args += ["--subtitulo", str(data["subtitulo"])]
    for key in ("inicio", "duracion"):
        value = data.get(key)
        if value not in (None, ""):
            args += [f"--{key}", str(float(value))]
    return args


def running_job():
    with jobs_lock:
        return next((j for j in jobs.values() if j["status"] == "running"), None)


def run_job(job_id, args):
    job = jobs[job_id]
    proc = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        line = line.rstrip()
        job["log"].append(line)
        if line.startswith("Audio"):
            job["stage"] = "Generando audio de piano…"
            job["progress"] = 2
        elif line.startswith("Video"):
            job["stage"] = "Dibujando las notas…"
            job["progress"] = 5
        elif m := PROGRESS_RE.search(line):
            done, total = float(m.group(1)), float(m.group(2))
            job["progress"] = 5 + 93 * done / total
    code = proc.wait()
    if code == 0:
        job.update(status="done", progress=100, stage="¡Listo!")
    else:
        job.update(status="error", stage="Falló la generación")


# ---------------------------------------------------------------- Rutas

@app.get("/")
def index():
    return send_from_directory(ROOT / "web", "index.html")


@app.get("/api/midis")
def list_midis():
    items = []
    for p in sorted(MIDI_DIR.glob("*.mid*")):
        try:
            length = round(mido.MidiFile(p).length, 1)
        except Exception:
            length = None
        items.append({"name": p.name, "length": length})
    return jsonify(items)


@app.post("/api/midis")
def upload_midi():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="No se recibió ningún archivo"), 400
    name = secure_filename(f.filename)
    if Path(name).suffix.lower() not in (".mid", ".midi"):
        return jsonify(error="El archivo debe ser .mid o .midi"), 400
    dest = MIDI_DIR / name
    f.save(dest)
    try:
        length = round(mido.MidiFile(dest).length, 1)
    except Exception:
        dest.unlink(missing_ok=True)
        return jsonify(error="No pude leer ese MIDI"), 400
    return jsonify(name=name, length=length)


@app.post("/api/preview")
def preview():
    data = request.get_json(force=True)
    midi = midi_path(data.get("midi"))
    if not midi:
        return jsonify(error="Elige un MIDI"), 400
    t = float(data.get("t") or 10)
    for old in PREVIEW_DIR.glob("*.png"):
        old.unlink(missing_ok=True)
    out = PREVIEW_DIR / f"{uuid.uuid4().hex[:8]}.mp4"
    args = build_args(data, midi) + ["--preview", str(t), "--salida", str(out)]
    res = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        return jsonify(error=(res.stderr or res.stdout).strip()[-600:]), 500
    png = Path(res.stdout.strip().splitlines()[-1])
    return jsonify(url=f"/out/.preview/{png.name}")


@app.post("/api/render")
def render():
    data = request.get_json(force=True)
    midi = midi_path(data.get("midi"))
    if not midi:
        return jsonify(error="Elige un MIDI"), 400
    if running_job():
        return jsonify(error="Ya hay un video generándose; espera a que termine"), 409
    name = slugify(data.get("titulo") or midi.stem)
    out = unique_output(name)
    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "status": "running", "progress": 0,
                        "stage": "Preparando…", "video": out.name, "log": [],
                        "started": time.time()}
    args = build_args(data, midi) + ["--salida", str(out)]
    threading.Thread(target=run_job, args=(job_id, args), daemon=True).start()
    return jsonify(id=job_id)


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify(error="No existe ese trabajo"), 404
    return jsonify({k: v for k, v in job.items() if k != "log"} | {"log": job["log"][-8:]})


@app.get("/api/jobs/current")
def current_job():
    job = running_job()
    return jsonify(id=job["id"] if job else None)


@app.get("/api/videos")
def list_videos():
    busy = {j["video"] for j in jobs.values() if j["status"] == "running"}
    meta = load_meta()
    items = []
    todos = [p for d in VIDEO_DIRS for p in d.glob("*.mp4")]
    for p in sorted(todos, key=lambda p: p.stat().st_mtime, reverse=True):
        if p.name in busy:
            continue
        st = p.stat()
        dur = video_duration(p, st.st_mtime)
        info = {"estado": "listo", "ia": False} | meta.get(p.name, {})
        carpeta = p.parent.name
        items.append({"name": p.name, "size": st.st_size, "mtime": st.st_mtime, "type": video_type(p.name),
                      "carpeta": carpeta, "url": f"/out/{carpeta}/{p.name}",
                      "duration": dur, "monetizable": bool(dur and dur >= MIN_MONETIZABLE)} | info)
    return jsonify(items)


@app.patch("/api/videos/<name>")
def update_video(name):
    """Cambia estado (listo/programado/publicado), fecha, descripción, hashtags o etiqueta de IA."""
    name = secure_filename(name)
    if not find_video(name):
        return jsonify(error="No existe ese video"), 404
    data = request.get_json(force=True)
    if "estado" in data and data["estado"] not in ESTADOS:
        return jsonify(error="Estado no válido"), 400
    with meta_lock:
        meta = load_meta()
        entry = meta.setdefault(name, {})
        for key in ("estado", "fecha", "descripcion", "hashtags", "titulo", "ia"):
            if key in data:
                entry[key] = data[key]
        if entry.get("estado") == "listo":
            entry.pop("fecha", None)
        save_meta(meta)
    return jsonify(entry)


@app.get("/api/ideas")
def list_ideas():
    return jsonify(load_ideas())


@app.post("/api/ideas")
def add_idea():
    data = request.get_json(force=True)
    titulo = str(data.get("titulo") or "").strip()
    if not titulo:
        return jsonify(error="Escribe la idea"), 400
    tipo = data.get("tipo") if data.get("tipo") in ("piano", "datos", "bolitas") else "datos"
    with meta_lock:
        doc = load_ideas()
        base = slugify(titulo)[:40]
        ids = {i["id"] for i in doc["ideas"]}
        idea_id, n = base, 2
        while idea_id in ids:
            idea_id, n = f"{base}-{n}", n + 1
        idea = {"id": idea_id, "tipo": tipo, "titulo": titulo, "estado": "idea"}
        doc["ideas"].insert(0, idea)
        save_meta(doc, IDEAS_FILE)
    return jsonify(idea)


@app.patch("/api/ideas/<idea_id>")
def update_idea(idea_id):
    data = request.get_json(force=True)
    if data.get("estado") not in ("idea", "hecho"):
        return jsonify(error="Estado no válido"), 400
    with meta_lock:
        doc = load_ideas()
        idea = next((i for i in doc["ideas"] if i["id"] == idea_id), None)
        if not idea:
            return jsonify(error="No existe esa idea"), 404
        idea["estado"] = data["estado"]
        save_meta(doc, IDEAS_FILE)
    return jsonify(idea)


@app.delete("/api/ideas/<idea_id>")
def delete_idea(idea_id):
    with meta_lock:
        doc = load_ideas()
        doc["ideas"] = [i for i in doc["ideas"] if i["id"] != idea_id]
        save_meta(doc, IDEAS_FILE)
    return jsonify(ok=True)


@app.get("/api/probar")
def list_probar():
    return jsonify(load_probar())


@app.post("/api/probar")
def add_probar():
    data = request.get_json(force=True)
    titulo = str(data.get("titulo") or "").strip()
    if not titulo:
        return jsonify(error="Escribe qué quieres probar"), 400
    enlace = str(data.get("enlace") or "").strip()
    if enlace and not enlace.startswith(("http://", "https://")):
        enlace = "https://" + enlace
    tipo = data.get("tipo") if data.get("tipo") in PROBAR_TIPOS else "otro"
    with meta_lock:
        doc = load_probar()
        base = slugify(titulo)[:40]
        ids = {i["id"] for i in doc["items"]}
        item_id, n = base, 2
        while item_id in ids:
            item_id, n = f"{base}-{n}", n + 1
        item = {"id": item_id, "tipo": tipo, "titulo": titulo, "enlace": enlace, "estado": "pendiente"}
        doc["items"].insert(0, item)
        save_meta(doc, PROBAR_FILE)
    return jsonify(item)


@app.patch("/api/probar/<item_id>")
def update_probar(item_id):
    data = request.get_json(force=True)
    if data.get("estado") not in ("pendiente", "probado"):
        return jsonify(error="Estado no válido"), 400
    with meta_lock:
        doc = load_probar()
        item = next((i for i in doc["items"] if i["id"] == item_id), None)
        if not item:
            return jsonify(error="No existe eso"), 404
        item["estado"] = data["estado"]
        save_meta(doc, PROBAR_FILE)
    return jsonify(item)


@app.delete("/api/probar/<item_id>")
def delete_probar(item_id):
    with meta_lock:
        doc = load_probar()
        doc["items"] = [i for i in doc["items"] if i["id"] != item_id]
        save_meta(doc, PROBAR_FILE)
    return jsonify(ok=True)


@app.get("/api/imagenes")
def list_images():
    items = []
    for p in sorted(OUT_DIR.glob("*.png")) + sorted((OUT_DIR / "avatares").glob("*.png")):
        items.append({"name": p.stem, "url": f"/out/{p.relative_to(OUT_DIR).as_posix()}?v={p.stat().st_mtime}"})
    return jsonify(items)


@app.delete("/api/videos/<name>")
def delete_video(name):
    path = find_video(name)
    if not path:
        return jsonify(error="No existe ese video"), 404
    path.unlink()
    with meta_lock:
        meta = load_meta()
        if meta.pop(path.name, None) is not None:
            save_meta(meta)
    return jsonify(ok=True)


@app.get("/out/<path:name>")
def serve_output(name):
    return send_from_directory(OUT_DIR, name)


if __name__ == "__main__":
    print("Neon Keys → http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)
