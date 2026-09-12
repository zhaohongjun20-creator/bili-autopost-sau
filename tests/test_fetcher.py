from src.fetcher import pick_videos, pick_video_file

FAKE_API_RESULT = {
    "videos": [
        {"id": 1, "width": 2160, "height": 3840, "duration": 10,
         "user": {"name": "A"}, "url": "https://pexels.com/v/1", "video_files": []},
        {"id": 2, "width": 1920, "height": 1080, "duration": 5,
         "user": {"name": "B"}, "url": "https://pexels.com/v/2", "video_files": []},
        {"id": 3, "width": 3840, "height": 2160, "duration": 120,
         "user": {"name": "C"}, "url": "https://pexels.com/v/3", "video_files": []},
    ]
}

def test_pick_videos_prefers_landscape_duration():
    vs = pick_videos(FAKE_API_RESULT, known_ids=set(), min_dur=60, max_dur=180, count=2)
    assert [v["id"] for v in vs] == [3]  # 1竖屏被滤，2太短被滤，只有3符合

def test_pick_videos_skips_known():
    vs = pick_videos(FAKE_API_RESULT, known_ids={3}, min_dur=60, max_dur=180, count=2)
    assert vs == []  # 全被去重

def test_pick_video_file():
    files = [
        {"link": "sd", "quality": "sd", "width": 640, "height": 360, "file_type": "video/mp4"},
        {"link": "fhd", "quality": "hd", "width": 1920, "height": 1080, "file_type": "video/mp4"},
        {"link": "uhd", "quality": "uhd", "width": 3840, "height": 2160, "file_type": "video/mp4"},
        {"link": "hls", "quality": "hd", "width": 1920, "height": 1080, "file_type": "video/x-mpegURL"},
    ]
    link = pick_video_file(files, max_height=1080)
    assert link == "fhd"  # ≤1080p 中最大，且排除 HLS 流
