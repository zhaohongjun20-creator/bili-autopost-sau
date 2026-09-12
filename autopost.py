"""bili-autopost-sau 入口：双画面蒙太奇 + BGM + 文学文案 → biliup 投稿。

用法：
  python autopost.py login      # 首次使用：扫码登录B站
  python autopost.py --dry-run  # 试跑（不投稿），检查 downloads/ 产出
  python autopost.py            # 完整流程并投稿（30秒双画面）
"""
import argparse, logging, os, random
from datetime import datetime
from dotenv import load_dotenv

from src.store import Store
from src.fetcher import search, pick_videos, pick_video_file, download
from src.copywriter import generate as gen_copy
from src.cover import extract_cover
from src.bgm import pick_bgm, BGM_CREDIT
from src.editor import make_dual_clip
import sau_bridge

LOG_DIR, DL_DIR, DATA_DIR = "logs", "downloads", "data"


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(f"{LOG_DIR}/{datetime.now():%Y-%m}.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_config():
    import yaml
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_material(log, cfg, store, count: int):
    """多关键词自动降级，选 count 个未用过的横屏素材。"""
    vf = cfg["video_filter"]
    keywords = cfg["keywords"][:]
    random.shuffle(keywords)
    for kw in keywords:
        log.info("搜索关键词: %s", kw)
        try:
            res = search(os.environ["PEXELS_API_KEY"], kw)
        except Exception as e:
            log.warning("搜索 %s 失败: %r，换下一个", kw, e)
            continue
        videos = pick_videos(res, known_ids=store.known_ids(),
                             min_dur=vf["min_duration"], max_dur=vf["max_duration"],
                             count=count)
        if len(videos) == count:
            return kw, videos
    return None, []


def run_once(dry_run: bool):
    log = logging.getLogger("main")
    load_dotenv()
    cfg = load_config()
    store = Store(f"{DATA_DIR}/published.db")
    seg = int(cfg.get("clip", {}).get("per_segment", 15))

    # ① fetch —— 两个不同画面
    keyword, videos = pick_material(log, cfg, store, count=2)
    if not videos:
        log.warning("所有关键词凑不齐 %d 个新素材，本次跳过", 2)
        return
    for v in videos:
        store.record_fetched(v["id"], keyword, v["url"])
        log.info("选中素材 pexels_id=%s 时长=%ss 作者=%s",
                 v["id"], v["duration"], v["user"]["name"])

    # ② download
    raw_paths = []
    for v in videos:
        link = pick_video_file(v["video_files"], cfg["download"]["max_height"])
        raw = f"{DL_DIR}/{v['id']}.mp4"
        if not os.path.exists(raw):
            log.info("下载中: %s", link)
            download(link, raw)
        log.info("已下载: %s (%.1f MB)", raw, os.path.getsize(raw) / 1e6)
        raw_paths.append(raw)

    # ③ 双画面合成 + BGM
    bgm_track = pick_bgm()
    final_path = f"{DL_DIR}/{videos[0]['id']}_dual.mp4"
    make_dual_clip(raw_paths[0], videos[0]["duration"],
                   raw_paths[1], videos[1]["duration"],
                   str(bgm_track), final_path, seg=seg)
    log.info("双画面合成: %s + BGM[%s] → %s (%.1f MB)",
             videos[0]["id"], bgm_track.name, final_path,
             os.path.getsize(final_path) / 1e6)

    # ④ metadata —— 双来源声明
    authors = [v["user"]["name"] for v in videos]
    copy = gen_copy(
        os.environ["ZHIPU_API_KEY"],
        {"keyword": keyword, "authors": authors,
         "duration": seg * 2, "orig_title": videos[0]["url"]},
        model=cfg["copywriter"]["model"],
        temperature=cfg["copywriter"]["temperature"],
    )
    copy["tags"] = list(dict.fromkeys(copy["tags"] + cfg["bilibili"]["tags_extra"]))[:10]
    sources = "；".join(f"{a}（{v['url']}）" for a, v in zip(authors, videos))
    copy["desc"] += f"\n素材来源：Pexels（免费商用授权），{sources}\n{BGM_CREDIT}"
    log.info("标题: %s", copy["title"])

    # ⑤ cover —— 取第一画面
    cover_path = f"{DL_DIR}/{videos[0]['id']}_cover.jpg"
    extract_cover(final_path, cover_path, at_second=max(1, seg // 2))
    log.info("封面: %s", cover_path)

    if dry_run:
        log.info("[DRY-RUN] 成片: %s\n简介:\n%s\n标签: %s",
                 final_path, copy["desc"], copy["tags"])
        return

    # ⑥ publish —— 走 social-auto-upload 的 biliup 运行时
    if not sau_bridge.check_account():
        log.error("B站登录态缺失/过期！请运行: python autopost.py login 重新扫码")
        for v in videos:
            store.mark_failed(v["id"], "biliup account expired")
        raise SystemExit(2)
    try:
        out = sau_bridge.upload(
            video_path=final_path, title=copy["title"], desc=copy["desc"],
            tags=copy["tags"], tid=cfg["bilibili"]["tid"], cover=cover_path,
            source_url=videos[0]["url"],
        )
        for v in videos:
            store.mark_published(v["id"], "biliup-ok")
        log.info("投稿成功。biliup 输出:\n%s", out)
        for p in [*raw_paths, final_path, cover_path]:
            os.remove(p)
    except Exception as e:
        for v in videos:
            store.mark_failed(v["id"], repr(e))
        log.exception("投稿失败，文件保留: %s", final_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("login", nargs="?", help="扫码登录B站")
    args = ap.parse_args()
    setup_logging()
    if args.login == "login":
        print("请在二维码出来后用B站APP扫码（若终端显示不全，打开 ./qrcode.png 扫描）")
        result = sau_bridge.login_interactive()
        print("登录退出码:", result.returncode)
        return
    run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
