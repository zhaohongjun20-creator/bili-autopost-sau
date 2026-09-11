# bili-autopost-sau

自动收集 Pexels 免费素材视频 → GLM 生成文案 → 经 **social-auto-upload 的 biliup 运行时**投稿到哔哩哔哩。

前代项目 [bilibili-autopost](https://github.com/zhaohongjun20-creator/bilibili-autopost)
（直接调 bilibili-api-python）已验证可行，本项目将发布环节切换到
[social-auto-upload](https://github.com/dreammis/social-auto-upload)（14.8k★）的
bilibili 运行时，投稿走 biliup（上传线路探测/断点续传/APP接口），未来可平滑扩展
抖音、小红书等多平台。

## 与前代的差异

| | bilibili-autopost（旧） | bili-autopost-sau（本） |
|---|---|---|
| 发布实现 | bilibili-api-python（逆向API） | biliup 二进制（social-auto-upload 运行时） |
| 登录 | 手动复制浏览器 cookie（月抛） | B站APP扫码，biliup 托管登录态 |
| 适配说明 | Python 3.14 直接可用 | biliup 由本项目自动下载管理（内联 runtime，同样兼容 3.14） |

## 用法

```bash
pip install requests pyyaml python-dotenv imageio-ffmpeg
cp .env.example .env       # 填 PEXELS_API_KEY / ZHIPU_API_KEY
python autopost.py login   # 首次：扫码登录B站（弹出终端窗口）
python autopost.py --dry-run
python autopost.py
```

素材收集/筛选/文案模块与前代一致：多关键词自动降级、横屏 60-180s 筛选、
SQLite 按 pexels_id 去重、GLM 文案自动附素材来源声明、ffmpeg 抽帧封面、
转载类型投稿（--copyright 2 --source）。

## 目录

```
autopost.py      入口（login / --dry-run / 完整投稿）
sau_bridge.py    biliup 运行时桥接（内联自 social-auto-upload runtime）
src/             fetcher / copywriter / cover / store
config.yaml      关键词、分区、模型
data/            biliup-account.json + published.db
```

## 合规

仅使用 Pexels License（免费商用）素材；按「转载」类型投稿并注明来源与原作者。
