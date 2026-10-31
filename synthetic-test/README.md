# 合成素材测试

本测试只由 FFmpeg 内置合成源生成画面和音调，不扫描或读取个人视频，不联网。每次运行创建新的时间戳目录，不覆盖之前结果。

```powershell
python .\synthetic-test\run_synthetic_test.py --ffmpeg "C:\绝对路径\ffmpeg.exe" --ffprobe "C:\绝对路径\ffprobe.exe"
```

要求 FFmpeg 包含 libx264、AAC 编码器、libass subtitles 滤镜，FFprobe 可执行；中文字体回退效果需人工确认。脚本先生成 6 秒测试片（2–4 秒静音），检测静音，再根据已知时间点剪成 4 秒竖屏片，加入合成背景音、基础调色与预写中英文字幕，并检查格式和完整解码。`timeline.json` 是可读剪辑计划记录，`test.log` 留有精确命令；修改计划后需要相应修改命令，它不是剪映等软件的项目文件。

`result.json` 记录每项结果；任何依赖或命令失败必须标记失败或阻塞。画面、字幕可读性与听感需要人工复核；合成音调不验证人声识别、智能删口癖、翻译质量、叙事或 B-roll。
