"""镜头运动检测：LK 光流估计机位运动量，淘汰固定机位的"明信片式"素材。

原理：稀疏光流追踪特征点，取位移模长的中位数——
运镜（推拉摇移/航拍）时绝大多数特征点同向移动，中位数大；
固定机位时仅局部物体（树叶/水波）在动，中位数趋近于零。
"""
import cv2
import numpy as np


def camera_motion_score(video_path: str, max_pairs: int = 30) -> float:
    """返回平均每帧机位位移（像素/帧）。越大越"有运镜"。"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if total < 2:
        cap.release()
        return 0.0
    # 均匀采样帧对，覆盖全片
    n_pairs = min(max_pairs, total - 1)
    stride = max(1, (total - 1) // n_pairs)
    idxs = list(range(0, total - 1, stride))[:n_pairs]

    feats = dict(maxCorners=150, qualityLevel=0.01, minDistance=30, blockSize=3)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
    mags = []
    prev_gray = None
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, frame = cap.read()
        if not ok:
            continue
        small = cv2.resize(frame, (960, 540))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            p0 = cv2.goodFeaturesToTrack(prev_gray, **feats)
            if p0 is not None and len(p0) >= 20:
                p1, st, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, p0, None)
                good = st.ravel() == 1
                if good.any():
                    d = p1[good] - p0[good]
                    mag = np.linalg.norm(d, axis=1)
                    mags.append(float(np.median(mag)))
        prev_gray = gray
    cap.release()
    if not mags:
        return 0.0
    return float(np.mean(mags))


def is_dynamic(video_path: str, threshold: float = 0.8) -> bool:
    """机位位移是否达到"有运镜"阈值（像素/帧，经验值）。"""
    return camera_motion_score(video_path) >= threshold
