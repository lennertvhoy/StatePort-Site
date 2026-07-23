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
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "assets" / "media"
NARRATION = MEDIA / "stateport-local-prototype-walkthrough-narration.txt"
OUT_MP4 = MEDIA / "stateport-local-prototype-walkthrough.mp4"
OUT_VTT = MEDIA / "stateport-local-prototype-walkthrough.vtt"
WORK = Path("/tmp/opencode/walkthrough-build")

VOICE = "en-US-AndrewNeural"
RATE = "+0%"
PITCH = "+0Hz"
GAP_S = 0.45          # silence between scenes
WIDTH, HEIGHT = 1280, 720
BG = "0x0B132B"
FPS = 30

# scene index -> screenshot file
SCENE_IMAGE = {
    0: "stateport-demo-home.png",
    1: "stateport-demo-home.png",
    2: "stateport-demo-conversation.png",
    3: "stateport-demo-source.png",
    4: "stateport-demo-mobile.png",
    5: "stateport-demo-mobile.png",
}
# scene index -> short caption title (first line of the VTT cue body)
SCENE_TITLE = {
    0: "A harness for coding agents",
    1: "The application you get",
    2: "The agent is replaceable",
    3: "Know what you can trust",
    4: "Take it with you",
    5: "Local preview",
}
SCENE_BODY = {
    0: "StatePort runs agents like Codex headlessly and gives the work a durable home outside the chat.",
    1: "Open a named project. Your state files and decisions live here, not hidden inside a session.",
    2: "Ask the agent for help in conversation. The work does not live or die with the chat.",
    3: "See what is ready, what is being checked, and what is only a test.",
    4: "The same project stays readable on a small screen.",
    5: "A local preview - not yet a public release. Harness the agent, govern what it does, keep the work.",
}


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], text=True)
    return float(out.strip())


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


def build_scene_clip(scene: int, audio: Path, image: Path, dst: Path) -> None:
    dur = probe_duration(audio)
    filt = image_filter(image)
    run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c={BG}:s={WIDTH}x{HEIGHT}:r={FPS}",
        "-loop", "1", "-i", str(image),
        "-i", str(audio),
        "-t", f"{dur:.3f}",
        "-filter_complex",
        f"[1:v]{filt},setsar=1[img];[0:v][img]overlay=x=(W-w)/2:y=(H-h)/2,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        "-shortest", str(dst),
    ])


def build_silence_clip(seconds: float, dst: Path) -> None:
    run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c={BG}:s={WIDTH}x{HEIGHT}:r={FPS}",
        "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", f"{seconds:.3f}",
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

    # 2. build a video clip per scene + silence transitions
    concat_list = WORK / "concat.txt"
    lines: list[str] = []
    scene_starts: list[float] = []
    scene_ends: list[float] = []
    cursor = 0.0
    n_scenes = len(paragraphs)
    for i, audio in enumerate(audio_files):
        clip = WORK / f"clip_{i}.mp4"
        build_scene_clip(i, audio, MEDIA / SCENE_IMAGE[i], clip)
        dur = probe_duration(clip)
        scene_starts.append(cursor)
        cursor += dur
        scene_ends.append(cursor)
        lines.append(f"file '{clip}'")
        if i < n_scenes - 1:
            sil = WORK / f"sil_{i}.mp4"
            build_silence_clip(GAP_S, sil)
            cursor += probe_duration(sil)
            lines.append(f"file '{sil}'")
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 3. concat -> final mp4
    run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", "-movflags", "+faststart", str(OUT_MP4),
    ])

    # 4. write VTT
    cues = ["WEBVTT", ""]
    for i in range(n_scenes):
        cues.append(fmt_ts(scene_starts[i]) + " --> " + fmt_ts(scene_ends[i]))
        cues.append(SCENE_TITLE[i])
        cues.append(SCENE_BODY[i])
        cues.append("")
    OUT_VTT.write_text("\n".join(cues), encoding="utf-8")

    total = probe_duration(OUT_MP4)
    print(f"\nWrote {OUT_MP4.relative_to(ROOT)} ({total:.2f}s)")
    print(f"Wrote {OUT_VTT.relative_to(ROOT)} ({n_scenes} cues)")


if __name__ == "__main__":
    main()
