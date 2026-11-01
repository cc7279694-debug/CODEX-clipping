# Phase 3C-R1：在普通 Windows PowerShell 准备 ASR 文件

本步骤只收集和核验候选依赖及模型，**不安装 faster-whisper 或其他 ASR 包、不加载模型、不转写音视频**。历史中的依赖下载阻塞与未运行项目仍然保留；准备成功也不代表模型或中文识别已验证。

## 运行前

- 打开本机的 `CODEX-clipping` 工作站文件夹：里面应能看到 `scripts`、`AI-Video-Workspace` 和 `STATUS.md`。
- 在该文件夹空白处打开普通 Windows PowerShell 或 Windows 终端的 PowerShell 窗口，**不需要管理员权限**。确认提示符所在位置是这个工作站文件夹。
- 保持网络可用，并预留足够磁盘空间。脚本只访问官方 PyPI 和 Systran 在 Hugging Face 的模型仓库及其白名单文件服务；遇到不能确认的跳转或超时会停止。

## 执行

在上述 PowerShell 中复制并运行：

```powershell
.\scripts\phase3c_prepare.ps1
```

脚本使用工作站现有的 Python 3.12.4 虚拟环境；如果其中没有 pip，会先通过 Python 自带的 `ensurepip` 将 pip 安装到**该虚拟环境内**。不会更改系统 Python，不安装 ASR 依赖，也不会使用 CUDA。它随后从官方文件元数据核对候选 wheel 的 SHA-256，并核对固定模型 revision 中各文件的官方 Git blob ID 或 LFS SHA-256。

如果 PowerShell 拒绝运行脚本、网络超时或提示 `BLOCKED`，请停下并记录提示；不要修改执行策略、防火墙、代理或安装未知程序。脚本每次使用新的随机结果目录；不要删除已有结果或反复重试。

## 判断结果

窗口最后会显示本地结果目录与状态。结果位于 `AI-Video-Workspace/phase3c-r1/runs/<时间-随机编号>/`：

- `FILES_VERIFIED_REVIEW_REQUIRED`：本次已获取文件并与查询到的官方文件元数据逐项比对；仍需检查依赖解析结果、许可证和后续离线安装。**不是模型加载、离线推理或中文识别通过。**
- `BLOCKED`：准备中途停止；可能已有部分下载文件，但它们不能当作完整成功结果，也不要手动安装。

成功时的目录包含 `wheelhouse/`、`model/`、`candidate-requirements.txt`、`wheel-metadata.json` 和 `collection-result.json`。依赖选择使用保守的候选解析；该清单**不是经完整解析器和离线安装验证的最终依赖锁**。遇到冲突、无法匹配的 wheel、未知文件来源或缺失哈希会停止。清单中的许可证元数据仍须逐项复核。

文件与官方元数据匹配是来源和完整性检查，不构成发布者数字签名证明。后续只有在完整依赖闭包、各许可证和哈希审查通过后，才能单独进行仅限该虚拟环境的离线安装；真实模型加载、缺文件受控失败、可控离线推理与中文语音冒烟需另行记录。

## 如何反馈

把终端最后显示的**状态**和简短错误类型反馈给 Codex，例如 `BLOCKED / TimeoutError` 或 `FILES_VERIFIED_REVIEW_REQUIRED`。为了进一步核对，可让 Codex 在本机读取该次 `collection-result.json` 和文件清单。

不要把完整屏幕输出直接公开发布：其中可能出现本地路径。不要上传下载的模型、wheel、视频、音频、转录、令牌、代理地址或私人日志；仅将脱敏状态反馈给 Codex。无需提供正式视频素材。
