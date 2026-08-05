import os
import sys
import threading
import webbrowser

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
import yt_dlp

app = FastAPI()

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_srt_time(seconds: float) -> str:
    seconds = max(0, seconds)
    total_ms = round(seconds * 1000)
    h, rem = divmod(total_ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_text(entries, fmt: str) -> str:
    if fmt == "srt":
        blocks = []
        for i, (start, duration, text) in enumerate(entries, start=1):
            end = start + max(duration, 1.0)
            blocks.append(
                f"{i}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{text}\n"
            )
        return "\n".join(blocks)
    if fmt == "timestamped":
        return "\n".join(f"[{format_time(start)}] {text}" for start, _, text in entries)
    return " ".join(text for _, _, text in entries if text.strip())


def extract_video_info(url: str):
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info


def try_get_captions(video_id: str, fmt: str):
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)

    transcript = None
    try:
        transcript = transcript_list.find_transcript(["ko", "en"])
    except NoTranscriptFound:
        for t in transcript_list:
            transcript = t
            break

    if transcript is None:
        return None

    fetched = transcript.fetch()
    entries = [
        (snippet.start, snippet.duration, snippet.text.replace("\n", " ").strip())
        for snippet in fetched
    ]
    entries = [(s, d, t) for s, d, t in entries if t]

    return {
        "language": transcript.language_code,
        "is_generated": transcript.is_generated,
        "text": build_text(entries, fmt),
    }


class ExtractRequest(BaseModel):
    url: str
    format: str = "srt"


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(BASE_DIR, "static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.post("/api/extract")
def extract(req: ExtractRequest):
    url = req.url.strip()
    if not url:
        return JSONResponse({"ok": False, "error": "Please provide a URL."}, status_code=400)

    try:
        info = extract_video_info(url)
        video_id = info.get("id")
        title = info.get("title", "")
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"Failed to fetch video info: {e}"}, status_code=400
        )

    fmt = req.format if req.format in ("plain", "timestamped", "srt") else "srt"

    try:
        result = try_get_captions(video_id, fmt) if video_id else None
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        return JSONResponse(
            {"ok": False, "error": f"This video has no captions: {e}"}, status_code=404
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"Failed to fetch captions: {e}"}, status_code=500
        )

    if not result:
        return JSONResponse(
            {"ok": False, "error": "This video has no captions."}, status_code=404
        )

    return {
        "ok": True,
        "source": "captions",
        "language": result["language"],
        "is_generated": result["is_generated"],
        "title": title,
        "text": result["text"],
    }


if __name__ == "__main__":
    import uvicorn

    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8787")).start()
    uvicorn.run(app, host="127.0.0.1", port=8787)
