"""双画面蒙太奇合成：两个素材各截一段，统一转码拼接，BGM 循环铺满。

一步 ffmpeg 完成（避免中间文件）：
  每段: scale+crop 到 1920x1080、fps 30（消除素材间参数差异，concat 才安全）
  拼接: concat filter；音频: 纯 BGM（30秒短片原声两段不一致反而突兀）
"""
import subprocess
from pathlib import Path
import imageio_ffmpeg

W, H, FPS = 1920, 1080, 30

def _seg_start(duration: int, seg: int) -> int:
    """片段起点：素材前 1/3 处，并保证剩余时长够截满 seg 秒。"""
    return max(0, min(int(duration) // 3, int(duration) - seg))

def make_dual_clip(raw_a: str, dur_a: int, raw_b: str, dur_b: int,
                   bgm_path: str, out_path: str, seg: int = 15,
                   bgm_vol: float = 1.0) -> str:
    """raw_a/raw_b 各截 seg 秒 → 拼接 → 铺 BGM，输出约 2*seg 秒成片。"""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS},setsar=1")
    fc = (f"[0:v]{vf}[v0];[1:v]{vf}[v1];"
          f"[v0][v1]concat=n=2:v=1:a=0[vout];"
          f"[2:a]volume={bgm_vol}[aout]")
    cmd = [
        ffmpeg, "-y",
        "-ss", str(_seg_start(dur_a, seg)), "-t", str(seg), "-i", raw_a,
        "-ss", str(_seg_start(dur_b, seg)), "-t", str(seg), "-i", raw_b,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    return out_path
