#!/usr/bin/env python3
"""Build the StatePort local-prototype walkthrough MP4 + WebVTT.

Reproducible build-time pipeline (no visitor-runtime voice dependency):

  narration paragraphs  --edge-tts-->  per-scene audio (en-US-AndrewNeural)
                                --ffmpeg-->  1280x720 MP4 (#0B132B night bg)
                                --compute--> WebVTT captions

Only public narration text leaves the machine, via the free public Edge TTS
endpoint, with no credentials. Re-run from the repo root:

  python3 scripts/build_walkthrough.py

Outputs are written next to the inputs in assets/media/. Requires ffmpeg,
ffprobe, and the `edge-tts` python package.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "assets" / "media"
NARRATION = MEDIA / "stateport-local-prototype-walkthrough-narration.txt"
NARRATION_SSML = MEDIA / "stateport-local-prototype-walkthrough-narration.ssml"
OUT_MP4 = MEDIA / "stateport-local-prototype-walkthrough.mp4"
OUT_VTT = MEDIA / "stateport-local-prototype-walkthrough.vtt"
OUT_MANIFEST = MEDIA / "stateport-local-prototype-walkthrough.manifest.json"
WORK = Path(os.environ.get("WALKTHROUGH_WORK_DIR", tempfile.gettempdir())) / "walkthrough-build"

VOICE = "en-US-AndrewNeural"
RATE = "-35%"
PITCH = "+0Hz"
GAP_S = 0.75          # quiet hold on the prior screen between scenes
WIDTH, HEIGHT = 1280, 720
BG = "0x0B132B"
FPS = 30

# scene index -> screenshot file
SCENE_IMAGE = {
    0: "stateport-platform-catalog.png",
    1: "stateport-platform-settings.png",
    2: "stateport-platform-conversation.png",
    3: "stateport-platform-settings.png",
    4: "stateport-platform-result.png",
    5: "stateport-platform-catalog.png",
    6: "stateport-platform-catalog.png",
}


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], text=True)
    return float(out.strip())


def probe_stream_duration(path: Path, selector: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", selector,
         "-show_entries", "stream=duration", "-of", "csv=p=0", str(path)],
        text=True,
    )
    return float(out.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def synth_scene(scene: int, text: str, dst: Path) -> None:
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await comm.save(str(dst))


def image_filter(image: Path) -> str:
    """Scale an image to fit the canvas height and return an overlay filter."""
    w, h = image_size(image)
    portrait = h > w
    if portrait:
        # fit to canvas height, keep aspect, even width
        return "scale=-2:%d" % HEIGHT
    # landscape: match the established 1152x720 placement
    return "scale=1152:%d" % HEIGHT


def image_size(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        text=True).strip()
    w, h = out.split(",")
    return int(w), int(h)


def build_scene_clip(scene: int, audio: Path, image: Path, dst: Path, hold: float) -> None:
    spoken_duration = probe_duration(audio)
    total_duration = spoken_duration + hold
    filt = image_filter(image)
    run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c={BG}:s={WIDTH}x{HEIGHT}:r={FPS}",
        "-loop", "1", "-i", str(image),
        "-i", str(audio),
        "-t", f"{total_duration:.3f}",
        "-filter_complex",
        f"[1:v]{filt},setsar=1[img];"
        f"[0:v][img]overlay=x=(W-w)/2:y=(H-h)/2,format=yuv420p[v];"
        f"[2:a]apad=pad_dur={hold:.3f},atrim=duration={total_duration:.3f}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        "-shortest", str(dst),
    ])


def fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def first_line(command: list[str]) -> str:
    return subprocess.check_output(command, text=True).splitlines()[0].strip()


def write_manifest(
    paragraphs: list[str], scene_starts: list[float], scene_ends: list[float]
) -> None:
    source_images = sorted({MEDIA / value for value in SCENE_IMAGE.values()})
    payload = {
        "schema": "stateport-walkthrough-build/v1",
        "rebuildCommand": "python3 scripts/build_walkthrough.py",
        "narrationContract": "seven exact public-copy paragraphs; one verbatim WebVTT cue per paragraph",
        "toolchain": {
            "edgeTts": importlib.metadata.version("edge-tts"),
            "ffmpeg": first_line(["ffmpeg", "-version"]),
            "voice": VOICE,
            "rate": RATE,
            "pitch": PITCH,
        },
        "video": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "gapSeconds": GAP_S,
            "durationSeconds": round(probe_duration(OUT_MP4), 3),
        },
        "inputs": {
            "builder": {
                "path": str(Path(__file__).resolve().relative_to(ROOT)),
                "sha256": sha256(Path(__file__).resolve()),
            },
            "narration": {
                "path": str(NARRATION.relative_to(ROOT)),
                "sha256": sha256(NARRATION),
            },
            "narrationMarkup": {
                "path": str(NARRATION_SSML.relative_to(ROOT)),
                "sha256": sha256(NARRATION_SSML),
            },
            "images": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                }
                for path in source_images
            ],
        },
        "scenes": [
            {
                "number": index + 1,
                "image": f"assets/media/{SCENE_IMAGE[index]}",
                "start": fmt_ts(scene_starts[index]),
                "end": fmt_ts(scene_ends[index]),
                "caption": re.sub(r"\s+", " ", paragraph).strip(),
            }
            for index, paragraph in enumerate(paragraphs)
        ],
        "outputs": {
            "mp4": {
                "path": str(OUT_MP4.relative_to(ROOT)),
                "sha256": sha256(OUT_MP4),
                "bytes": OUT_MP4.stat().st_size,
            },
            "vtt": {
                "path": str(OUT_VTT.relative_to(ROOT)),
                "sha256": sha256(OUT_VTT),
                "bytes": OUT_VTT.stat().st_size,
            },
        },
    }
    OUT_MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"missing required tool: {tool}")
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        sys.exit("missing python package: pip install --user edge-tts")

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    paragraphs = [p.strip() for p in NARRATION.read_text(encoding="utf-8").split("\n\n") if p.strip()]
    if len(paragraphs) != len(SCENE_IMAGE):
        sys.exit(f"narration has {len(paragraphs)} paragraphs, expected {len(SCENE_IMAGE)}")

    # 1. synth audio per scene
    audio_files: list[Path] = []
    for i, text in enumerate(paragraphs):
        clean = re.sub(r"\s+", " ", text).strip()
        dst = WORK / f"scene_{i}.mp3"
        asyncio.run(synth_scene(i, clean, dst))
        audio_files.append(dst)
        print(f"  scene {i}: {probe_duration(dst):.2f}s")

    # 2. build one video clip per scene. The final 0.75 seconds holds the
    # current UI screen while the audio rests, avoiding blank transition cards.
    concat_list = WORK / "concat.txt"
    lines: list[str] = []
    scene_starts: list[float] = []
    scene_ends: list[float] = []
    cursor = 0.0
    n_scenes = len(paragraphs)
    for i, audio in enumerate(audio_files):
        clip = WORK / f"clip_{i}.mp4"
        spoken_duration = probe_duration(audio)
        hold = GAP_S if i < n_scenes - 1 else 0.0
        build_scene_clip(i, audio, MEDIA / SCENE_IMAGE[i], clip, hold)
        scene_starts.append(cursor)
        scene_ends.append(cursor + spoken_duration)
        lines.append(f"file '{clip}'")
        cursor += probe_duration(clip)
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 3. concat -> final mp4 via the concat filter (full re-encode).
    # The concat *demuxer* with stream copy corrupts the AAC timeline of
    # these clips (audio drifts ~30s past the video); the filter rebuilds
    # both streams from decoded frames and stays exact.
    filter_inputs: list[str] = []
    for line in lines:
        clip_path = line.split("'")[1]
        filter_inputs.extend(["-i", clip_path])
    concat_segments = "".join(f"[{index}:v][{index}:a]" for index in range(len(lines)))
    run([
        "ffmpeg", "-y", "-v", "error",
        *filter_inputs,
        "-filter_complex", f"{concat_segments}concat=n={len(lines)}:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        "-movflags", "+faststart", str(OUT_MP4),
    ])

    # 4. write VTT — exactly one verbatim cue per narration paragraph.
    # Use the measured final audio-stream duration for the final cue endpoint.
    scene_ends[-1] = probe_stream_duration(OUT_MP4, "a:0")
    cues = ["WEBVTT", ""]
    for i in range(n_scenes):
        text = re.sub(r"\s+", " ", paragraphs[i]).strip()
        cues.append(fmt_ts(scene_starts[i]) + " --> " + fmt_ts(scene_ends[i]))
        cues.extend(textwrap.wrap(text, width=54, break_long_words=False, break_on_hyphens=False))
        cues.append("")
    OUT_VTT.write_text("\n".join(cues), encoding="utf-8")
    write_manifest(paragraphs, scene_starts, scene_ends)

    total = probe_duration(OUT_MP4)
    print(f"\nWrote {OUT_MP4.relative_to(ROOT)} ({total:.2f}s)")
    print(f"Wrote {OUT_VTT.relative_to(ROOT)} ({n_scenes} cues)")
    print(f"Wrote {OUT_MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
