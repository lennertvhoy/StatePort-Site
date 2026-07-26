#!/usr/bin/env python3
"""Build and validate the public-safe StatePort walkthrough media.

The narration text is canonical for this media package. A successful build
derives matching SSML and WebVTT, synthesizes per-scene audio at build time,
renders only the declared public-safe screenshots, and publishes the MP4 and
its exact evidence manifest only after validation succeeds.

Only public narration text is sent to the Edge TTS service. Visitors have no
runtime voice dependency. Run from the repository root:

  python3 scripts/build_walkthrough.py
  python3 scripts/build_walkthrough.py --validate-only
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "assets" / "media"
NARRATION = MEDIA / "stateport-local-prototype-walkthrough-narration.txt"
OUT_SSML = MEDIA / "stateport-local-prototype-walkthrough-narration.ssml"
OUT_MP4 = MEDIA / "stateport-local-prototype-walkthrough.mp4"
OUT_VTT = MEDIA / "stateport-local-prototype-walkthrough.vtt"
OUT_MANIFEST = MEDIA / "stateport-local-prototype-walkthrough.manifest.json"

VOICE = "en-US-AndrewNeural"
RATE = "+0%"
PITCH = "+0Hz"
GAP_S = 0.45
WIDTH, HEIGHT = 1280, 720
BACKGROUND = "0x0B132B"
FPS = 30
AUDIO_RATE = 48_000
DURATION_TOLERANCE_S = 0.08

SCENE_IMAGES = (
    "stateport-demo-home.png",
    "stateport-demo-home.png",
    "stateport-demo-conversation.png",
    "stateport-demo-source.png",
    "stateport-demo-mobile.png",
    "stateport-demo-mobile.png",
)

TIMESTAMP_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}\.\d{3}) --> "
    r"(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})$"
)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_narration(path: Path = NARRATION) -> list[str]:
    paragraphs = [
        normalize(paragraph)
        for paragraph in path.read_text(encoding="utf-8").split("\n\n")
        if paragraph.strip()
    ]
    if len(paragraphs) != len(SCENE_IMAGES):
        raise ValueError(
            f"narration has {len(paragraphs)} scenes; expected {len(SCENE_IMAGES)}"
        )
    return paragraphs


def probe_duration(path: Path) -> float:
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        text=True,
    )
    return float(output.strip())


def probe_media(path: Path) -> dict[str, object]:
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            (
                "format=duration:stream=index,codec_type,codec_name,duration,"
                "width,height,r_frame_rate,sample_rate,channels"
            ),
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    return json.loads(output)


def image_size(path: Path) -> tuple[int, int]:
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(path),
        ],
        text=True,
    ).strip()
    width, height = output.split(",")
    return int(width), int(height)


def image_filter(path: Path) -> str:
    width, height = image_size(path)
    if height > width:
        return f"scale=-2:{HEIGHT}"
    return f"scale=1152:{HEIGHT}"


async def synthesize(text: str, destination: Path) -> None:
    import edge_tts

    communication = edge_tts.Communicate(
        text,
        VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communication.save(str(destination))


def build_scene_clip(
    audio: Path,
    image: Path,
    destination: Path,
    tail_seconds: float,
) -> tuple[float, float]:
    speech_duration = probe_duration(audio)
    total_duration = speech_duration + tail_seconds
    audio_filter = f"[2:a]aresample={AUDIO_RATE}:first_pts=0"
    if tail_seconds:
        audio_filter += f",apad=pad_dur={tail_seconds:.3f}"
    audio_filter += "[audio]"
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={BACKGROUND}:s={WIDTH}x{HEIGHT}:r={FPS}",
            "-framerate",
            str(FPS),
            "-loop",
            "1",
            "-i",
            str(image),
            "-i",
            str(audio),
            "-t",
            f"{total_duration:.6f}",
            "-filter_complex",
            (
                f"[1:v]{image_filter(image)},setsar=1[image];"
                f"[0:v][image]overlay=x=(W-w)/2:y=(H-h)/2,format=yuv420p[video];"
                f"{audio_filter}"
            ),
            "-map",
            "[video]",
            "-map",
            "[audio]",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            str(AUDIO_RATE),
            "-ac",
            "2",
            str(destination),
        ]
    )
    return speech_duration, probe_duration(destination)


def concatenate(clips: list[Path], concat_list: Path, destination: Path) -> None:
    concat_list.write_text(
        "".join(f"file '{clip.as_posix()}'\n" for clip in clips),
        encoding="utf-8",
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-fflags",
            "+genpts",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-fps_mode",
            "cfr",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            str(AUDIO_RATE),
            "-ac",
            "2",
            "-avoid_negative_ts",
            "make_zero",
            "-movflags",
            "+faststart",
            "-shortest",
            str(destination),
        ]
    )


def format_timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds_value, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_value:02d}.{milliseconds:03d}"


def parse_timestamp(value: str) -> float:
    hours, minutes, remainder = value.split(":")
    seconds, milliseconds = remainder.split(".")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def write_vtt(path: Path, cues: list[dict[str, object]]) -> None:
    lines = ["WEBVTT", ""]
    for cue in cues:
        lines.extend(
            [
                (
                    f"{format_timestamp(float(cue['startSeconds']))} --> "
                    f"{format_timestamp(float(cue['endSeconds']))}"
                ),
                str(cue["text"]),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_vtt(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "WEBVTT":
        raise ValueError(f"{path}: missing WEBVTT header")
    cues: list[dict[str, object]] = []
    index = 1
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        match = TIMESTAMP_RE.fullmatch(lines[index].strip())
        if not match:
            raise ValueError(f"{path}: invalid cue timestamp at line {index + 1}")
        index += 1
        caption_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            caption_lines.append(lines[index].strip())
            index += 1
        if len(caption_lines) != 1:
            raise ValueError(
                f"{path}: each cue must contain one verbatim caption line"
            )
        cues.append(
            {
                "startSeconds": parse_timestamp(match.group("start")),
                "endSeconds": parse_timestamp(match.group("end")),
                "text": normalize(caption_lines[0]),
            }
        )
    return cues


def write_ssml(path: Path, paragraphs: list[str]) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<speak version="1.1" xml:lang="en-US">',
        f'  <voice name="{VOICE}">',
        f'    <prosody rate="{RATE}" pitch="{PITCH}">',
    ]
    for index, paragraph in enumerate(paragraphs, start=1):
        lines.append(
            f'      <p id="scene-{index:02d}">{escape(paragraph)}</p>'
        )
    lines.extend(["    </prosody>", "  </voice>", "</speak>", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_ssml(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    paragraphs = root.findall(".//p")
    return [normalize("".join(paragraph.itertext())) for paragraph in paragraphs]


def stream_facts(media: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    streams = media.get("streams")
    if not isinstance(streams, list):
        raise ValueError("ffprobe did not return streams")
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1 or len(audio_streams) != 1:
        raise ValueError("walkthrough must contain exactly one video and one audio stream")
    return video_streams[0], audio_streams[0]


def validate_package(
    narration_path: Path,
    ssml_path: Path,
    vtt_path: Path,
    mp4_path: Path,
) -> tuple[list[str], list[dict[str, object]], dict[str, object]]:
    paragraphs = load_narration(narration_path)
    ssml_paragraphs = parse_ssml(ssml_path)
    cues = parse_vtt(vtt_path)
    if ssml_paragraphs != paragraphs:
        raise ValueError("SSML text does not exactly match narration scenes")
    if [cue["text"] for cue in cues] != paragraphs:
        raise ValueError("WebVTT text does not exactly match narration scenes")
    if len(cues) != len(SCENE_IMAGES):
        raise ValueError("WebVTT cue count does not match declared scenes")
    if abs(float(cues[0]["startSeconds"])) > 0.001:
        raise ValueError("first WebVTT cue must start at zero")
    for previous, current in zip(cues, cues[1:]):
        if float(previous["endSeconds"]) >= float(current["startSeconds"]):
            raise ValueError("WebVTT cues overlap or are not ordered")
        observed_gap = float(current["startSeconds"]) - float(previous["endSeconds"])
        if abs(observed_gap - GAP_S) > DURATION_TOLERANCE_S:
            raise ValueError(
                f"WebVTT inter-scene gap is {observed_gap:.3f}s; expected {GAP_S:.3f}s"
            )

    media = probe_media(mp4_path)
    video, audio = stream_facts(media)
    video_duration = float(video["duration"])
    audio_duration = float(audio["duration"])
    final_caption_end = float(cues[-1]["endSeconds"])
    if abs(video_duration - audio_duration) > DURATION_TOLERANCE_S:
        raise ValueError(
            "walkthrough stream duration mismatch: "
            f"video={video_duration:.6f}s audio={audio_duration:.6f}s"
        )
    if abs(final_caption_end - audio_duration) > DURATION_TOLERANCE_S:
        raise ValueError(
            "final caption does not align with media end: "
            f"caption={final_caption_end:.3f}s audio={audio_duration:.6f}s"
        )
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise ValueError("walkthrough must use H.264 video and AAC audio")
    if int(video.get("width", 0)) != WIDTH or int(video.get("height", 0)) != HEIGHT:
        raise ValueError(f"walkthrough must be {WIDTH}x{HEIGHT}")
    if int(audio.get("sample_rate", 0)) != AUDIO_RATE:
        raise ValueError(f"walkthrough audio must use {AUDIO_RATE} Hz")
    if int(audio.get("channels", 0)) != 2:
        raise ValueError("walkthrough audio must be stereo")
    return paragraphs, cues, media


def rounded(value: object) -> float:
    return round(float(value), 6)


def build_manifest(
    paragraphs: list[str],
    cues: list[dict[str, object]],
    media: dict[str, object],
    ssml_path: Path,
    vtt_path: Path,
    mp4_path: Path,
) -> dict[str, object]:
    video, audio = stream_facts(media)
    scenes = []
    for index, (paragraph, cue, image_name) in enumerate(
        zip(paragraphs, cues, SCENE_IMAGES, strict=True),
        start=1,
    ):
        image_path = MEDIA / image_name
        scenes.append(
            {
                "id": f"scene-{index:02d}",
                "image": f"assets/media/{image_name}",
                "imageSha256": sha256_file(image_path),
                "startSeconds": rounded(cue["startSeconds"]),
                "endSeconds": rounded(cue["endSeconds"]),
                "caption": paragraph,
            }
        )
    return {
        "formatVersion": "stateport-walkthrough-media/v1",
        "claimBoundary": {
            "availability": "private_alpha_fixture_not_public_release",
            "executionProvider": "codex",
            "executionMode": "supervised_direct",
            "otherProvidersQualified": False,
            "shownViews": [
                "applications_home_and_catalog",
                "application_conversation",
                "application_source_status",
                "mobile_applications_home",
            ],
        },
        "ownershipSeam": {
            "statePortOwns": [
                "intent",
                "authority",
                "canonical_state",
                "evidence",
                "acceptance",
            ],
            "harnessOwns": "authorized_execution_behavior",
        },
        "build": {
            "voice": VOICE,
            "rate": RATE,
            "pitch": PITCH,
            "sceneGapSeconds": GAP_S,
            "width": WIDTH,
            "height": HEIGHT,
            "framesPerSecond": FPS,
            "audioSampleRateHz": AUDIO_RATE,
            "durationToleranceSeconds": DURATION_TOLERANCE_S,
            "builder": "scripts/build_walkthrough.py",
            "builderSha256": sha256_file(Path(__file__)),
        },
        "scenes": scenes,
        "artifacts": {
            "narration": {
                "path": "assets/media/stateport-local-prototype-walkthrough-narration.txt",
                "sha256": sha256_file(NARRATION),
                "sceneCount": len(paragraphs),
            },
            "ssml": {
                "path": "assets/media/stateport-local-prototype-walkthrough-narration.ssml",
                "sha256": sha256_file(ssml_path),
                "sceneCount": len(paragraphs),
            },
            "vtt": {
                "path": "assets/media/stateport-local-prototype-walkthrough.vtt",
                "sha256": sha256_file(vtt_path),
                "cueCount": len(cues),
                "lastCueEndSeconds": rounded(cues[-1]["endSeconds"]),
            },
            "mp4": {
                "path": "assets/media/stateport-local-prototype-walkthrough.mp4",
                "sha256": sha256_file(mp4_path),
                "formatDurationSeconds": rounded(media["format"]["duration"]),
                "videoDurationSeconds": rounded(video["duration"]),
                "audioDurationSeconds": rounded(audio["duration"]),
                "videoCodec": video["codec_name"],
                "audioCodec": audio["codec_name"],
                "width": int(video["width"]),
                "height": int(video["height"]),
                "audioSampleRateHz": int(audio["sample_rate"]),
                "audioChannels": int(audio["channels"]),
            },
        },
    }


def write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_manifest(path: Path) -> dict[str, object]:
    paragraphs, cues, media = validate_package(NARRATION, OUT_SSML, OUT_VTT, OUT_MP4)
    expected = build_manifest(paragraphs, cues, media, OUT_SSML, OUT_VTT, OUT_MP4)
    actual = json.loads(path.read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("walkthrough manifest does not match the exact media package")
    return expected


def build() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(f"missing required tool: {tool}")
    try:
        import edge_tts  # noqa: F401
    except ImportError as error:
        raise RuntimeError("missing python package: edge-tts") from error

    paragraphs = load_narration()
    with tempfile.TemporaryDirectory(
        prefix=".stateport-walkthrough-",
        dir=MEDIA,
    ) as temporary_directory:
        work = Path(temporary_directory)
        candidate_ssml = work / OUT_SSML.name
        candidate_vtt = work / OUT_VTT.name
        candidate_mp4 = work / OUT_MP4.name
        candidate_manifest = work / OUT_MANIFEST.name
        write_ssml(candidate_ssml, paragraphs)

        clips: list[Path] = []
        cues: list[dict[str, object]] = []
        cursor = 0.0
        for index, (text, image_name) in enumerate(
            zip(paragraphs, SCENE_IMAGES, strict=True)
        ):
            audio = work / f"scene-{index + 1:02d}.mp3"
            asyncio.run(synthesize(text, audio))
            clip = work / f"scene-{index + 1:02d}.mp4"
            tail = GAP_S if index < len(paragraphs) - 1 else 0.0
            speech_duration, clip_duration = build_scene_clip(
                audio,
                MEDIA / image_name,
                clip,
                tail,
            )
            cues.append(
                {
                    "startSeconds": cursor,
                    "endSeconds": cursor + speech_duration,
                    "text": text,
                }
            )
            cursor += clip_duration
            clips.append(clip)
            print(
                f"scene {index + 1:02d}: speech={speech_duration:.3f}s "
                f"clip={clip_duration:.3f}s image={image_name}"
            )

        write_vtt(candidate_vtt, cues)
        concatenate(clips, work / "concat.txt", candidate_mp4)
        paragraphs, cues, media = validate_package(
            NARRATION,
            candidate_ssml,
            candidate_vtt,
            candidate_mp4,
        )
        manifest = build_manifest(
            paragraphs,
            cues,
            media,
            candidate_ssml,
            candidate_vtt,
            candidate_mp4,
        )
        write_manifest(candidate_manifest, manifest)

        for candidate, destination in (
            (candidate_ssml, OUT_SSML),
            (candidate_vtt, OUT_VTT),
            (candidate_mp4, OUT_MP4),
            (candidate_manifest, OUT_MANIFEST),
        ):
            os.replace(candidate, destination)

    manifest = validate_manifest(OUT_MANIFEST)
    media_facts = manifest["artifacts"]["mp4"]
    print(
        f"wrote {OUT_MP4.relative_to(ROOT)} "
        f"({media_facts['formatDurationSeconds']:.3f}s, "
        f"sha256 {media_facts['sha256']})"
    )
    print(f"wrote {OUT_VTT.relative_to(ROOT)} ({len(paragraphs)} verbatim cues)")
    print(f"wrote {OUT_SSML.relative_to(ROOT)}")
    print(f"wrote {OUT_MANIFEST.relative_to(ROOT)}")


def validate_only() -> None:
    for tool in ("ffprobe",):
        if not shutil.which(tool):
            raise RuntimeError(f"missing required tool: {tool}")
    manifest = validate_manifest(OUT_MANIFEST)
    media_facts = manifest["artifacts"]["mp4"]
    print(
        "walkthrough validation: OK; "
        f"{len(manifest['scenes'])} scenes; "
        f"video={media_facts['videoDurationSeconds']:.6f}s; "
        f"audio={media_facts['audioDurationSeconds']:.6f}s; "
        f"sha256={media_facts['sha256']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate committed narration, SSML, captions, media, and manifest",
    )
    arguments = parser.parse_args()
    try:
        if arguments.validate_only:
            validate_only()
        else:
            build()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"walkthrough build failed: {error}")


if __name__ == "__main__":
    main()
