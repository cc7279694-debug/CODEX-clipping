# Phase 3C：中文 ASR 环境与真实模型验证

日期：2026-10-31。**整体 BLOCKED，停在独立验收点**；Phase 3B 仍为 PARTIAL，Phase 2C 仍为 PARTIAL / WAITING_USER_CHECK，不申请 ACCEPTED 或 FROZEN。

## 基线与工作区

开始时 GitHub `main` 的 HEAD 为 `b07cdb648e6342da8b6e15dcf7e9ef26c9c36878`，与指定基线一致。通过 GitHub API 读取基线：当前本地工作目录没有 `.git`，因此无法执行通常意义的 `git pull` 或判定 Git 未提交状态。已逐项核对相关文件，保留本地和远端 README 各自的原有内容；`tests/test_asr.py` 的 Git blob 不同但文本内容一致。没有覆盖或发布未核对的本地文件。本报告以远端 HEAD 为父提交并用预期 SHA 防止误覆盖远端更新。

## 检查结果

| 项目 | 状态 | 本轮证据及边界 |
| --- | --- | --- |
| 独立 Python 环境 | PASS（解释器） | 工作区 `AI-Video-Workspace/phase3b/.venv` 为 Python 3.12.4；`python -m pip --version` 显示无 pip，`faster_whisper`、`ctranslate2`、`huggingface_hub` 未找到。没有安装任何包。 |
| 资源 | PASS（瞬时读数） | 可用物理内存约 3.79 GiB，工作卷可用约 33.22 GiB；不保证实际模型能运行。 |
| 官方依赖及模型准备 | BLOCKED | 受限执行环境访问 PyPI 官方 JSON 5 秒超时。Hugging Face 元数据一次 HTTP 200，但未验证正文或最终地址；随后读取及固定修订模型权重的 HEAD 在现有连接路径超时。单次 200 不能证明可靠获取。没有下载或安装依赖、模型。 |
| 普通 Windows 用户终端 | UNKNOWN | 本轮未在独立的普通用户终端直接测试，不可由 Codex 沙箱结果推断。下方提供最小对照。检索服务能读取网页也不证明本机可下载二进制文件。 |
| 实际模型加载、CPU int8、模型内存与耗时 | NOT_RUN | 未取得包和完整模型；没有实际安装版本、依赖锁、经过下载核验的模型 revision 或文件哈希，不能声称加载成功。 |
| 真实模型缺 tokenizer / 权重时受控失败 | NOT_RUN | 模拟文件预检覆盖缺 tokenizer、权重损坏；与真实模型和引擎运行不同，缺真实权重测试也未完成。 |
| 真实离线推理 | NOT_RUN | Python socket guard 的单元测试不能证明 C/C++ 原生代码和子进程离线。没有进行关闭系统网络等操作。 |
| 中文合成语音、转写、ASR 时间戳、SRT、源哈希及性能 | NOT_RUN | 无可用完整真实模型；此前也未取得可靠中文合成语音，不以纯音或英文冒充。 |
| 现有逻辑回归 | PASS | 独立 venv 中设置 `PYTHONPATH=src`，运行 `python -m unittest discover -s tests -q`，41 项通过，退出码 0；使用模拟数据，不能证明模型加载、识别质量或真实离线推理。 |
| 真人识别准确率、字幕边界误差、讲话及笑声误删率 | NOT_RUN | 需经授权的测试语音和独立人工参考标注；本轮不读取正式素材、不执行删剪。 |

没有更改代理、防火墙、DNS、UAC、显卡驱动或系统安全设置；未安装 CUDA，未修改 OpenFilm 或剪映及其工程。之前 Phase 3B 的失败记录与报告保持原样。

## 安全补充审查

- `src/codex_clipping/asr.py` 的 manifest 预检验证 revision 格式、目录文件与自填 SHA-256 一致，不连接官方源，也不验证 revision 真实性或签名。如果文件与清单一起被替换仍可能通过；**清单预检 PASS 不等于可信来源或实际模型加载 PASS**。导入前须独立核对固定 revision 官方文件身份及可信元数据；为全部实际文件生成 SHA-256 清单只能用于后续完整性检测。
- `pipeline.py` 在 ASR 失败后清空转录，可能写出空 SRT，但 `subtitles` 为 NOT_RUN；不得将文件存在视作字幕生成成功。逻辑覆盖不代表真实模型失败路径已运行。
- `media.py` 对未知或超过容差的非零格式、音频／视频起点受控拒绝；手机 MP4 如不满足条件保持 BLOCKED，不猜测或修复时间偏移。
- 低电平候选不证明无低声讲话、笑声或自然停顿。人工保护标注和可编辑审核 JSON 是待复核声明，并非真实性、安全性证明；每个建议须人工听看，不会自动剪切。源码中 Python 层离线保护也不是操作系统级隔离证明。

## 普通 Windows 用户会话的最小对照

打开普通 PowerShell，逐行运行以下只读请求，每个地址各请求一次，最多等待 5 秒；只返回状态或错误类型，不上传本机视频，也不改变网络设置。不要粘贴含个人信息的完整代理或环境变量：

```powershell
$urls = @('https://pypi.org/pypi/faster-whisper/json', 'https://huggingface.co/api/models/Systran/faster-whisper-base')
foreach ($url in $urls) {
  try { $r = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing; Write-Host "$url : HTTP $($r.StatusCode)" }
  catch { Write-Host "$url : FAILED ($($_.Exception.GetType().Name))" }
}
```

HTTP 200 仅是该次元数据请求成功；依赖 wheel、模型权重实际下载及文件验证需单独确认。若超时，停止重试并记录结果，不切换不明镜像。普通终端和浏览器能否访问目前均为 UNKNOWN。

## 官方获取清单与离线导入方案（待实施）

仅当普通用户会话或官方浏览器渠道可可靠访问时实施；不上传任何音视频。以下是准备方案，不表示文件已下载或安装：

1. 固定 [Systran/faster-whisper-base 官方模型](https://huggingface.co/Systran/faster-whisper-base) 的一个明确 40 位 revision，在对应 revision 的 Files 页面确认全部文件。当前研究中的[候选 revision 文件树](https://huggingface.co/Systran/faster-whisper-base/tree/a80717a3a48b1b28aa687bca146cb7301feae1b1)列有 `config.json`、`model.bin`、`tokenizer.json`、`vocabulary.txt`、`README.md` 等；导入时以所选 revision 的完整实际列表为准，连同许可证信息一并核对。官方模型卡标示 MIT、多语言；不得将候选 revision 说成已下载或已核验。
2. 针对选定 revision，从 Hugging Face 官方文件元数据分别记录文件标识：LFS 文件使用官方 SHA-256，普通 Git 文件可核对官方 Git blob 对象 ID；再计算本地 SHA-256 写入 manifest。必须按所选 revision 对照，不能用 `main` 的摘要冒充固定修订证据。官方提供的元数据及 HTTPS 是信任依据，不是发布者签名。未能独立核对时保持 BLOCKED。
3. 从 [PyPI faster-whisper](https://pypi.org/project/faster-whisper/) 及各依赖自己的 PyPI 页面获取适合 Windows x64 / Python 3.12 的 wheel。候选 faster-whisper 1.2.1 标示 MIT、Python ≥3.9；需先解析全部传递依赖（包括 CTranslate2），逐项记录精确版本、wheel 文件名、官方列出的 SHA-256 和各自许可证，生成完整锁文件。不能用自算摘要或 `pip freeze` 单独冒充官方验证；不使用 GPU/CUDA 或第三方镜像。
4. 可联网的同架构 Python 3.12 终端可按 [pip download 官方说明](https://pip.pypa.io/en/stable/cli/pip_download/) 收集 wheelhouse；如仅浏览器能访问，则手工收集完整 wheel 和官方元数据。依赖闭包、哈希或兼容性有任何缺项时先停止，不安装。
5. 在隔离 venv 中准备 pip（`python -m ensurepip` 使用该 Python 自带的 pip，仍需记录其版本；不可用则停止）。仅在完整可信锁和所有 wheel 核对后，以本地 wheelhouse 和锁文件运行：`python -m pip install --no-index --find-links <wheelhouse> --require-hashes -r <verified-lock.txt>`；检查安装版本和 `pip check`。所有路径需替换为本机独立工作区路径，不使用管理员权限。
6. 将经过官方文件身份核对的模型放入独立本地目录，记录实际 revision、各文件 SHA-256、实际安装包版本及许可证，按 [Phase 3B 使用说明](../PHASE3B-USAGE.md) 制作 manifest 并运行 `check-model`。再分别验证实际 CPU int8 模型加载、缺 tokenizer 和权重时的受控失败、可控离线推理。`check-model` 本身不加载模型。每一步留本地脱敏记录；模型、wheel、媒体及私人日志不提交到公开仓库。

## 下一步

先取得普通 Windows PowerShell 上两项对照结果，再决定是否使用官方渠道收集文件并完成全部核对。若仍无法获取，保持 BLOCKED。即使模型加载成功，也需明确授权的可丢弃中文语音才能测试中文识别；真人质量要另外人工标注验收。停止在独立审查点，不自动进入正式剪辑。
