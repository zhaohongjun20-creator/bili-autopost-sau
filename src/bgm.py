"""BGM 混音：随机选取本地曲库，原声压低保留氛围、BGM 循环对齐视频时长。

曲库为 Kevin MacLeod (incompetech.com) 的 CC-BY 作品，简介需自动署名。
"""
import os, random, subprocess
from pathlib import Path
import imageio_ffmpeg

BGM_DIR = Path(__file__).parent.parent / "bgm"
BGM_CREDIT = "BGM: Kevin MacLeod (incompetech.com), CC BY 4.0"

def pick_bgm() -> Path:
    tracks = sorted(BGM_DIR.glob("*.mp3"))
    if not tracks:
        raise FileNotFoundError(f"no bgm in {BGM_DIR}")
    return random.choice(tracks)

def _has_audio(video_path: str, ffmpeg: str) -> bool:
    r = subprocess.run([ffmpeg, "-i", video_path], capture_output=True, text=True, timeout=60)
    return "Audio:" in (r.stderr or "")

def mix_bgm(video_path: str, bgm_path: str, out_path: str,
           voice_vol: float = 0.25, bgm_vol: float = 1.0) -> str:
    """原声压低至 voice_vol 与 BGM 混合；视频无音轨则直接铺 BGM。视频流不重编码。"""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if _has_audio(video_path, ffmpeg):
        afilter = (f"[0:a]volume={voice_vol}[va];[1:a]volume={bgm_vol}[ba];"
                   f"[va][ba]amix=inputs=2:duration=first:dropout_transition=3:normalize=0[aout]")
        amap = ["-map", "0:v", "-map", "[aout]"]
    else:
        afilter = f"[1:a]volume={bgm_vol}[aout]"
        amap = ["-map", "0:v", "-map", "[aout]"]
    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,   # BGM 无限循环
        "-filter_complex", afilter, *amap,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    return out_path
