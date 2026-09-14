@echo off
rem 计划任务入口：切换到本目录后执行完整流水线（双画面+BGM+投稿），日志追加到 logs\task.log
cd /d %~dp0
python autopost.py >> logs\task.log 2>&1
