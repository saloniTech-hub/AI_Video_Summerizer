import os
import tempfile
import requests
import traceback
import math
import time
import uuid
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import ffmpeg
from dotenv import load_dotenv

# load .env
load_dotenv()

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
    raise RuntimeError("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env")

WHISPER_MODEL = "@cf/openai/whisper"
LLAMA_MODEL = "@cf/meta/llama-3.1-8b-instruct"

CHUNK_SECONDS = 15
CHUNK_RETRY_ATTEMPTS = 3
CHUNK_RETRY_DELAY = 2
CHUNK_SEND_DELAY = 0.7

app = Flask(__name__)
CORS(app)

# In-memory job store. For production use persistent store (Redis, DB).
jobs = {}  # job_id -> {state, progress, chunk, total_chunks, transcript, summary, error}

# -----------------------
# Utility helpers
# -----------------------
def safe_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def extract_audio(video_path, wav_path):
    # synchronous ffmpeg call; ensures file closed before continuing
    try:
        (
            ffmpeg
            .input(video_path)
            .output(wav_path, ac=1, ar="16000")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        err = getattr(e, "stderr", None)
        raise Exception("FFmpeg failed: " + (err.decode() if isinstance(err, bytes) else str(e)))

def get_audio_duration(path):
    try:
        info = ffmpeg.probe(path)
        return float(info["format"]["duration"])
    except Exception as e:
        raise Exception(f"Could not probe audio duration: {e}")

def call_cloudflare_whisper_bytes(audio_bytes_list):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{WHISPER_MODEL}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"audio": audio_bytes_list}

    last_data = None
    for attempt in range(1, CHUNK_RETRY_ATTEMPTS + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            data = resp.json()
        except Exception as e:
            last_data = {"error": str(e)}
            if attempt < CHUNK_RETRY_ATTEMPTS:
                time.sleep(CHUNK_RETRY_DELAY)
                continue
            raise Exception(f"Network/HTTP error calling Cloudflare: {e}")

        last_data = data
        if data.get("success", False):
            # extract text
            res = data.get("result", {})
            text = None
            if isinstance(res, dict):
                text = res.get("text") or res.get("transcription") or res.get("response")
                if not text:
                    out = res.get("output")
                    if isinstance(out, list) and out:
                        first = out[0]
                        if isinstance(first, dict) and first.get("content"):
                            content = first["content"]
                            if isinstance(content, list) and content:
                                c0 = content[0]
                                if isinstance(c0, dict) and c0.get("text"):
                                    text = c0.get("text")
            if text:
                return text
            # if success true but no text found, return str(res)
            return str(res)

        # If errors: retry on transient messages
        errs = data.get("errors", [])
        if errs and isinstance(errs, list):
            msg0 = errs[0].get("message", "") if isinstance(errs[0], dict) else str(errs[0])
            if ("Unknown error" in msg0) or ("busy" in msg0.lower()) or ("timeout" in msg0.lower()):
                if attempt < CHUNK_RETRY_ATTEMPTS:
                    time.sleep(CHUNK_RETRY_DELAY)
                    continue
                else:
                    raise Exception(f"Cloudflare Whisper Error (after retries): {data}")
            else:
                # non-transient
                raise Exception(f"Cloudflare Whisper Error: {data}")

        # generic fallback: retry
        if attempt < CHUNK_RETRY_ATTEMPTS:
            time.sleep(CHUNK_RETRY_DELAY)
            continue
        else:
            raise Exception(f"Cloudflare Whisper final failure: {data or last_data}")

    raise Exception(f"Cloudflare Whisper final failure: {last_data}")

def call_cloudflare_llama(text):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{LLAMA_MODEL}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You are an assistant that produces short, clear bullet summaries."},
            {"role": "user", "content": text}
        ]
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    data = resp.json()
    if not data.get("success", False):
        raise Exception(f"Cloudflare Llama Error: {data}")
    res = data.get("result", {})
    # prefer direct fields
    if isinstance(res, dict):
        return res.get("response") or res.get("text") or res.get("transcription") or str(res)
    return str(res)

# -----------------------
# Background worker
# -----------------------
def process_job(job_id, video_path):
    """
    Background worker: extracts audio, splits into chunks, sends to Cloudflare,
    updates jobs[job_id] with progress and final results.
    """
    try:
        jobs[job_id]["state"] = "extracting_audio"
        # create wav temp
        wav_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav_path = wav_tmp.name
        wav_tmp.close()

        extract_audio(video_path, wav_path)

        # ensure ffmpeg finished and file closed before proceeding
        duration = get_audio_duration(wav_path)
        total_chunks = max(1, math.ceil(duration / CHUNK_SECONDS))
        jobs[job_id]["total_chunks"] = total_chunks
        jobs[job_id]["state"] = "transcribing"
        jobs[job_id]["chunk"] = 0

        transcripts = []
        for idx in range(total_chunks):
            jobs[job_id]["chunk"] = idx + 1
            jobs[job_id]["progress"] = round(((idx) / total_chunks) * 100, 1)
            # create segment temp
            seg_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            seg_path = seg_tmp.name
            seg_tmp.close()

            # cut chunk: use -ss and -t
            try:
                (
                    ffmpeg
                    .input(wav_path, ss=idx * CHUNK_SECONDS)
                    .output(seg_path, t=CHUNK_SECONDS, ac=1, ar="16000")
                    .overwrite_output()
                    .run(quiet=True)
                )
            except ffmpeg.Error as e:
                safe_remove(seg_path)
                raise Exception(f"FFmpeg chunk creation failed: {e}")

            # read bytes and send as list of ints
            try:
                with open(seg_path, "rb") as sf:
                    raw = sf.read()
                audio_bytes = list(raw)
            except Exception as e:
                safe_remove(seg_path)
                raise Exception(f"Failed read chunk bytes: {e}")

            # remove segment file asap
            safe_remove(seg_path)

            # transcribe chunk
            text = call_cloudflare_whisper_bytes(audio_bytes)
            transcripts.append(text.strip())

            # small delay to avoid bursts
            time.sleep(CHUNK_SEND_DELAY)

        # combine transcript
        full_transcript = " ".join([t for t in transcripts if t])
        jobs[job_id]["transcript"] = full_transcript
        jobs[job_id]["state"] = "summarizing"
        jobs[job_id]["progress"] = 95

        # summarize (may chunk again if huge)
        # keep simple: call llama on entire transcript; if very large, it still works (or you can chunk)
        final_summary = call_cloudflare_llama(full_transcript)
        jobs[job_id]["summary"] = final_summary
        jobs[job_id]["state"] = "done"
        jobs[job_id]["progress"] = 100

    except Exception as e:
        # store error
        jobs[job_id]["state"] = "error"
        jobs[job_id]["error"] = str(e)
        traceback.print_exc()
    finally:
        # cleanup uploaded video and wav if exist
        safe_remove(video_path)
        # wav may exist at wav_path variable; try to remove
        try:
            if 'wav_path' in locals():
                safe_remove(wav_path)
        except Exception:
            pass

# -----------------------
# API endpoints
# -----------------------
@app.route("/process", methods=["POST"])
def start_process():
    """
    Starts a background job. Returns {job_id}.
    """
    try:
        if "video" not in request.files:
            return jsonify({"error": "No video file uploaded (use field name 'video')"}), 400

        uploaded = request.files["video"]
        filename = secure_filename(uploaded.filename or "upload.mp4")

        tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1] or ".mp4")
        uploaded.save(tmp_video.name)
        tmp_video_path = tmp_video.name
        tmp_video.close()

        job_id = str(uuid.uuid4())
        # initialize job metadata
        jobs[job_id] = {
            "state": "queued",
            "progress": 0,
            "chunk": 0,
            "total_chunks": 0,
            "transcript": "",
            "summary": "",
            "error": None
        }

        # start background thread
        t = threading.Thread(target=process_job, args=(job_id, tmp_video_path), daemon=True)
        t.start()

        return jsonify({"job_id": job_id})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/status/<job_id>", methods=["GET"])
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)

@app.route("/jobs", methods=["GET"])
def list_jobs():
    return jsonify(list(jobs.keys()))

# -----------------------
# run server
# -----------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)