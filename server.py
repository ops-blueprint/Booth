"""Booth: a free, offline voice-over studio. Run: .venv/bin/python server.py"""

from __future__ import annotations

import io
import logging
import os
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

from app import engines as E  # noqa: E402
from app.studio import DATA, RENDERS, Studio, _read_json, _write_json  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("booth")

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
PORT = int(os.environ.get("BOOTH_PORT", "7863"))

app = FastAPI(title="Booth", docs_url=None, redoc_url=None)
studio = Studio()


def wav_bytes(a: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(a, -1, 1), E.SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def fail(e: Exception, code: int = 400):
    raise HTTPException(status_code=code, detail=str(e) or e.__class__.__name__)


# ------------------------------------------------------------------ status

@app.get("/api/status")
def status():
    ok, why = studio.clone.available()
    return {"kokoro": studio.kokoro.ready(), "clone": ok, "clone_reason": why,
            "clone_state": studio.clone.state, "ffmpeg": bool(E.have_ffmpeg()),
            "busy": any(j["status"] in ("queued", "running") for j in studio.jobs.values()),
            "disk_gb": round(E.free_disk_gb(), 1), "min_disk_gb": E.MIN_FREE_DISK_GB}


# ------------------------------------------------------------------ voices

@app.get("/api/voices")
def voices():
    return studio.list_voices()


@app.post("/api/voices/clone")
async def clone_voice(name: str = Form(""), ref_text: str = Form(""), file: UploadFile = File(...)):
    suffix = Path(file.filename or "sample.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        path = Path(tmp.name)
    try:
        return studio.create_clone(name, path, ref_text)
    except Exception as e:
        fail(e)
    finally:
        path.unlink(missing_ok=True)


class BlendIn(BaseModel):
    name: str = ""
    a: str
    b: str
    ratio: float = 0.5


@app.post("/api/voices/blend")
def blend_voice(body: BlendIn):
    try:
        return studio.create_blend(body.name, body.a, body.b, body.ratio)
    except Exception as e:
        fail(e)


class VoicePatch(BaseModel):
    name: str | None = None
    ref_text: str | None = None


@app.patch("/api/voices/{vid}")
def patch_voice(vid: str, body: VoicePatch):
    try:
        return studio.update_voice(vid, body.name, body.ref_text)
    except Exception as e:
        fail(e)


@app.delete("/api/voices/{vid}")
def delete_voice(vid: str):
    try:
        studio.delete_voice(vid)
        return {"ok": True}
    except Exception as e:
        fail(e)


@app.get("/api/voices/{vid}/sample")
def voice_sample(vid: str):
    try:
        return FileResponse(studio.voice_sample(vid), media_type="audio/wav")
    except Exception as e:
        fail(e)


@app.get("/api/voices/{vid}/reference")
def voice_reference(vid: str):
    p = DATA / "voices" / vid / "ref.wav"
    if not p.exists():
        raise HTTPException(404, "No reference audio")
    return FileResponse(p, media_type="audio/wav")


# ------------------------------------------------------------------ speaking

class SpeakIn(BaseModel):
    text: str
    voice: str
    speed: float = 1.0


@app.post("/api/preview")
def preview(body: SpeakIn):
    text = body.text.strip()
    if not text:
        fail(ValueError("Nothing to read."))
    if len(text) > 1200:
        text = text[:1200]
    try:
        from app.script import parse
        segs = parse(text, 0.3, 0.6, group=False)
        parts = []
        for s in segs[:12]:
            parts.append(studio.speak(s.text, body.voice, body.speed))
            parts.append(np.zeros(int(s.pause_after * E.SR), dtype=np.float32))
        a = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        return Response(wav_bytes(a), media_type="audio/wav")
    except Exception as e:
        fail(e)


class TextIn(BaseModel):
    text: str
    voice: str = "am_michael"


@app.post("/api/analyze")
def analyze(body: TextIn):
    from app.script import parse
    segs = parse(body.text)
    words = len(body.text.split())
    return {"lines": len(segs), "words": words, "minutes": round(words / 150, 1),
            "review": studio.review_words(body.text),
            "spoken": studio.explain(body.text, body.voice)}


# ------------------------------------------------------------------ renders

class RenderIn(BaseModel):
    script: str
    voice: str
    speed: float = 1.0
    sentence_gap: float = 0.3
    paragraph_gap: float = 0.8
    title: str = ""


@app.post("/api/render")
def render(body: RenderIn):
    if not body.script.strip():
        fail(ValueError("Type or paste a script first."))
    try:
        studio.get_voice(body.voice)
    except Exception as e:
        fail(e)
    return studio.submit("render", **body.model_dump())


class RedoIn(BaseModel):
    text: str | None = None


@app.post("/api/renders/{rid}/segments/{index}/redo")
def redo(rid: str, index: int, body: RedoIn):
    meta = _read_json(RENDERS / rid / "meta.json")
    if not meta or index >= len(meta.get("segments", [])):
        fail(KeyError("Line not found"), 404)
    return studio.submit("redo", render_id=rid, index=index, text=body.text)


@app.get("/api/jobs/{jid}")
def job(jid: str):
    j = studio.jobs.get(jid)
    if not j:
        raise HTTPException(404, "Job not found")
    return studio.public_job(j)


@app.post("/api/jobs/{jid}/cancel")
def cancel(jid: str):
    studio.cancel(jid)
    return {"ok": True}


@app.get("/api/renders")
def renders():
    return studio.renders()


@app.get("/api/renders/{rid}")
def render_meta(rid: str):
    try:
        return studio.render_meta(rid)
    except Exception as e:
        fail(e, 404)


@app.delete("/api/renders/{rid}")
def delete_render(rid: str):
    try:
        studio.delete_render(rid)
        return {"ok": True}
    except Exception as e:
        fail(e)


def _safe_name(title: str) -> str:
    import re
    s = re.sub(r"[^\w\- ]+", "", title or "voiceover").strip().replace(" ", "-")
    return (s or "voiceover")[:60]


@app.get("/api/renders/{rid}/voiceover.wav")
def render_wav(rid: str, download: int = 0):
    p = RENDERS / rid / "voiceover.wav"
    if not p.exists():
        raise HTTPException(404, "Not ready")
    meta = _read_json(RENDERS / rid / "meta.json", {})
    name = _safe_name(meta.get("title")) + ".wav" if download else None
    return FileResponse(p, media_type="audio/wav", filename=name)


@app.get("/api/renders/{rid}/voiceover.mp3")
def render_mp3(rid: str):
    try:
        meta = _read_json(RENDERS / rid / "meta.json", {})
        return FileResponse(studio.mp3(rid), media_type="audio/mpeg", filename=_safe_name(meta.get("title")) + ".mp3")
    except Exception as e:
        fail(e)


@app.get("/api/renders/{rid}/subtitles.srt")
def render_srt(rid: str):
    p = RENDERS / rid / "subtitles.srt"
    if not p.exists():
        raise HTTPException(404, "Not ready")
    meta = _read_json(RENDERS / rid / "meta.json", {})
    return FileResponse(p, media_type="application/x-subrip", filename=_safe_name(meta.get("title")) + ".srt")


@app.get("/api/renders/{rid}/segments/{index}.wav")
def render_segment(rid: str, index: int):
    p = RENDERS / rid / "segments" / f"{index:04d}.wav"
    if not p.exists():
        raise HTTPException(404, "Not ready")
    return FileResponse(p, media_type="audio/wav", headers={"Cache-Control": "no-store"})


# ------------------------------------------------------------------ dictionary

@app.get("/api/lexicon")
def lexicon(q: str = "", limit: int = 400):
    items = studio.lexicon.entries()
    if q:
        ql = q.lower()
        items = [e for e in items if ql in e["word"].lower() or ql in (e.get("say") or "").lower()
                 or ql == (e.get("tag") or "").lower()]
    return {"total": len(items), "items": items[:limit]}


class LexIn(BaseModel):
    word: str
    say: str = ""
    ipa: str = ""
    exact: bool = False


@app.post("/api/lexicon")
def lexicon_add(body: LexIn):
    try:
        return studio.lexicon.upsert(body.word, body.say, body.ipa, "custom", body.exact)
    except Exception as e:
        fail(e)


@app.delete("/api/lexicon/{word}")
def lexicon_delete(word: str):
    return {"ok": studio.lexicon.delete(word)}


class LexTest(BaseModel):
    word: str
    say: str = ""
    ipa: str = ""
    voice: str = "am_michael"
    context: str = ""


@app.post("/api/lexicon/test")
def lexicon_test(body: LexTest):
    """Hear a word the way an entry would say it, without saving it."""
    word = body.word.strip()
    if not word:
        fail(ValueError("Type a word first."))
    if body.ipa.strip():
        token = f"[{word}](/{body.ipa.strip().strip('/')}/)"
    elif body.say.strip():
        token = f"[{word}]({body.say.strip()})"
    else:
        token = word
    text = body.context.replace(word, token, 1) if body.context and word in body.context else token + "."
    try:
        return Response(wav_bytes(studio.speak(text, body.voice)), media_type="audio/wav")
    except Exception as e:
        fail(e)


# ------------------------------------------------------------------ draft

@app.get("/api/draft")
def get_draft():
    return _read_json(DATA / "draft.json", {"title": "", "script": "", "voice": "am_michael", "speed": 1.0})


@app.put("/api/draft")
def put_draft(body: dict):
    _write_json(DATA / "draft.json", body)
    return {"ok": True}


# ------------------------------------------------------------------ web

app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})


@app.exception_handler(Exception)
async def on_error(request, exc):
    log.exception("unhandled")
    return JSONResponse({"detail": str(exc)}, status_code=500)


def warm():
    try:
        studio.kokoro.k
        log.info("Built-in voices ready.")
    except Exception as e:
        log.error("Could not load the voice model: %s", e)


if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=warm, daemon=True).start()
    url = f"http://127.0.0.1:{PORT}"
    if "--no-browser" not in sys.argv:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"\n  Booth is running at {url}\n  Keep this window open while you work. Close it to stop.\n")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
