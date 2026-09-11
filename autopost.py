"""bili-autopost-sau 入口：Pexels素材 + GLM文案 + social-auto-upload(biliup)投稿。

用法：
  python autopost.py login      # 首次使用：扫码登录B站
  python autopost.py --dry-run  # 试跑（不投稿），检查 downloads/ 产出
  python autopost.py            # 完整流程并投稿
"""
import argparse, logging, os, random
from datetime import datetime
from dotenv import load_dotenv

from src.store import Store
from src.fetcher import search, pick_video, pick_video_file, download
from src.copywriter import generate as gen_copy
from src.cover import extract_cover
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


def pick_material(log, cfg, store):
    """多关键词自动降级选一个未用过的横屏素材。"""
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
        video = pick_video(res, known_ids=store.known_ids(),
                           min_dur=vf["min_duration"], max_dur=vf["max_duration"])
        if video:
            return kw, video
    return None, None


def run_once(dry_run: bool):
    log = logging.getLogger("main")
    load_dotenv()
    cfg = load_config()
    store = Store(f"{DATA_DIR}/published.db")

    # ① fetch
    keyword, video = pick_material(log, cfg, store)
    if not video:
        log.warning("所有关键词均无可用新素材，本次跳过")
        return
    store.record_fetched(video["id"], keyword, video["url"])
    log.info("选中素材 pexels_id=%s 时长=%ss 作者=%s",
             video["id"], video["duration"], video["user"]["name"])

    # ② download
    link = pick_video_file(video["video_files"], cfg["download"]["max_height"])
    video_path = f"{DL_DIR}/{video['id']}.mp4"
    if not os.path.exists(video_path):
        log.info("下载中: %s", link)
        download(link, video_path)
    log.info("已下载: %s (%.1f MB)", video_path, os.path.getsize(video_path) / 1e6)

    # ③ metadata
    copy = gen_copy(
        os.environ["ZHIPU_API_KEY"],
        {"keyword": keyword, "author": video["user"]["name"],
         "duration": video["duration"], "orig_title": video["url"]},
        model=cfg["copywriter"]["model"],
        temperature=cfg["copywriter"]["temperature"],
    )
    copy["tags"] = list(dict.fromkeys(copy["tags"] + cfg["bilibili"]["tags_extra"]))[:10]
    log.info("标题: %s", copy["title"])

    # ④ cover
    cover_path = f"{DL_DIR}/{video['id']}_cover.jpg"
    extract_cover(video_path, cover_path)
    log.info("封面: %s", cover_path)

    if dry_run:
        log.info("[DRY-RUN] 简介:\n%s\n标签: %s", copy["desc"], copy["tags"])
        return

    # ⑤ publish —— 走 social-auto-upload 的 biliup 运行时
    if not sau_bridge.check_account():
        log.error("B站登录态缺失/过期！请运行: python autopost.py login 重新扫码")
        store.mark_failed(video["id"], "biliup account expired")
        raise SystemExit(2)
    try:
        out = sau_bridge.upload(
            video_path=video_path, title=copy["title"], desc=copy["desc"],
            tags=copy["tags"], tid=cfg["bilibili"]["tid"], cover=cover_path,
            source_url=video["url"],
        )
        store.mark_published(video["id"], "biliup-ok")
        log.info("投稿成功。biliup 输出:\n%s", out)
        os.remove(video_path)
        os.remove(cover_path)
    except Exception as e:
        store.mark_failed(video["id"], repr(e))
        log.exception("投稿失败，文件保留: %s", video_path)


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
