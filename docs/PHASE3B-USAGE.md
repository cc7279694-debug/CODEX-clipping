# Phase 3B 本地命令与限制

当前基础代码可独立测试；真实中文转写因官方依赖/模型下载不可达而未验证。独立环境位于 `AI-Video-Workspace/phase3b/.venv`，只有 Python 3.12.4，未装 pip、faster-whisper 或模型。不要把下列命令当作已经完成的 ASR 操作。

从仓库根设置当前进程模块搜索路径，不改变系统配置：

```powershell
$taskRoot = (Get-Location).Path
$env:PYTHONPATH = Join-Path $taskRoot 'src'
& .\AI-Video-Workspace\phase3b\.venv\Scripts\python.exe -m codex_clipping --help
```

## 依赖和模型准备

网络允许后，只从 [官方 PyPI](https://pypi.org/project/faster-whisper/) 和 [Systran 官方模型](https://huggingface.co/Systran/faster-whisper-base) 取得包与模型。依赖解析和下载属于单独的准备步骤；锁定实际 wheel、全部传递依赖版本及 SHA-256，固定模型 commit revision，并核对许可。当前没有可称为实际 lock 的文件，不能复制单元测试中的虚构版本/哈希使用。

首测候选为多语言 `base`、CPU int8、2 线程、单进程；资源充足且验证通过后再评估 small。不启用 GPU。模型目录只包含实际审核过的资源和 `model-manifest.json`，其结构为：

```json
{
  "schema_version": 1,
  "repository": "Systran/faster-whisper-base",
  "revision": "<actual-40-character-commit>",
  "model": "base",
  "files": {
    "model.bin": "<actual-sha256>",
    "config.json": "<actual-sha256>",
    "tokenizer.json": "<actual-sha256>"
  },
  "packages": {
    "faster-whisper": "<actual-installed-version>",
    "ctranslate2": "<actual-installed-version>",
    "tokenizers": "<actual-installed-version>",
    "av": "<actual-installed-version>",
    "huggingface-hub": "<actual-installed-version>",
    "onnxruntime": "<actual-installed-version>",
    "tqdm": "<actual-installed-version>",
    "numpy": "<actual-installed-version>"
  }
}
```

这是不可直接运行的结构示例；`files` 必须覆盖该固定模型目录的全部实际文件（例如另有 vocabulary 或 preprocessor 配置时也须包含），`packages` 记录全部实际运行依赖。哈希仅证明与清单相符，清单来源仍须独立核验，不能将自填清单视作官方签名或真实模型加载通过。不要手工篡改配置以绕过版本错误。

`check-model --model <local-model-directory>` 只验证文件、路径、JSON、revision 格式和 SHA-256，不加载模型。`analyze` 才会比对实际包版本并在 Python 进程局部离线保护下调用 faster-whisper；保护不等同 OS 级断网，真实原生依赖的离线行为仍需另外验证。

## 分析测试语音

仅指定明确授权、可丢弃的中文测试素材。准备就绪后：

```powershell
& .\AI-Video-Workspace\phase3b\.venv\Scripts\python.exe -m codex_clipping analyze `
  --source '<authorized-test-media>' --out '<new-output-directory>' `
  --ffmpeg (Join-Path $taskRoot 'OpenFilm\resources\runtime\ffmpeg\ffmpeg.exe') `
  --ffprobe (Join-Path $taskRoot 'OpenFilm\resources\runtime\ffmpeg\ffprobe.exe') `
  --model '<verified-local-model-directory>' --threads 2
```

工具读取元数据、提取只供分析的 16 kHz 单声道 WAV、检测低电平区间，然后尝试本地中文转写；输出 `metadata.json`、`transcript.srt`、`silence-candidates.json`、`edit-decisions.json`。输出目录必须是新的，使用独占创建；不覆盖源文件或已有结果。源 SHA-256 前后不同则结果失效。仅支持已知接近零的媒体和音轨起点；非零或未知起点明确阻塞，不猜偏移。保留源时间，未支持的复杂音轨应单独报告。

ASR 失败时仍可能留下元数据/静音结果及空 SRT；以 `metadata.json` 的阶段状态为准。空 SRT 不算字幕生成通过，空转写不证明没有低声讲话。状态 `READY_FOR_REVIEW` 只表示代码流程完成，文字、时间戳和剪辑建议还需人工审核。

## 建议、接受、拒绝和撤销

分析阶段默认保护证据不完整，所有静音区间只进入候选或排除记录，不自动生成可接受的删除建议。完整检查讲话、笑声和自然停顿后，人工标注 JSON 应含 `schema_version: 1`、对应的 `source_sha256`、`protection_reviewed: true` 和 `protected_intervals` 数组；每项含 `start`、`end`、`kind`（speech/laughter/natural_pause），全部为源秒数。此声明来自人工，不是自动保护保证。

使用 `propose --decisions <analysis/edit-decisions.json> --silence <analysis/silence-candidates.json> --annotations <manual-labels.json> --source <same-test-media> --out <new-proposal.json>` 生成新建议版本。它要求有可校验的转写/静音字段和源哈希，但 JSON 字段不是不可伪造的 ASR 来源认证；测试数据不可用于质量验收。任何候选碰到保护区或识别语句边缘都会被排除，合格建议默认 pending。

使用 `review --input <decisions.json> --source <same-test-media> --id <cut-id> --action accept|reject|undo --out <new-review.json>`。每次操作写新文件并保留历史；撤销回退该建议最近仍有效的审核动作。即使 accepted 也不执行任何视频剪切。没有删剪/导出命令，不改 OpenFilm 或剪映工程。

## 测试范围

运行 `python -m unittest discover -s tests -v`（先设置 PYTHONPATH）。假模型字节只验证预检，手写中文只验证 SRT 排版，测试替身只验证流程与审核；它们不能作为真实模型、中文 ASR 或真人误删性能证据。资源统计是当前 Python 进程的 CPU 时间和生命周期峰值工作集，不含 FFmpeg 子进程；没有模型时不能称为 ASR benchmark。原始测试产物、转录和模型不上传公开仓库。
