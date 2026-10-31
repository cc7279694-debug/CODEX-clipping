# 集中测试记录

日期：2026-10-31；总状态：**BLOCKED**。测试仅使用 FFmpeg 生成的合成素材。

| 项目 | 结果 | 证据及限制 |
| --- | --- | --- |
| A. Codex 发现剪映 MCP | NOT_RUN | MCP 未安装和注册；当前会话工具列表未发现对应工具。没有将工具清单搜索当成 MCP 握手验证 |
| B. 读取测试素材时长、画幅、帧率 | PASS | FFprobe 直接读取两段合成视频，各 3 秒、360×640、25 fps；不是 MCP 的读取测试 |
| C. 两段以上视频时间线计划 | PASS | `tests/synthetic-fixtures/edit-plan.json` 包含两段素材及时间位置；已检查文件引用和字幕时间。仅为计划，不是剪映草稿 |
| D. 加入至少两条中文字幕 | NOT_RUN | 两条文本已写入 SRT 和计划，但未生成剪映字幕轨 |
| E. 独立背景音频轨 | NOT_RUN | 已生成合成 WAV 并记录计划，未创建实际草稿轨道 |
| F. 片段裁剪与转场 | NOT_RUN | 已记录裁剪与 0.2 秒转场计划，未创建或播放草稿 |
| G. `dry_run=true` | NOT_RUN | 依赖未安装；源码显示 dry-run 也写暂存并清理，未执行 |
| H. 唯一测试草稿发布 | BLOCKED | 兼容性未知，发布清理存在竞态，草稿根不在当前写入范围；没有创建测试草稿 |
| I. 草稿、素材引用与轨道结构校验 | NOT_RUN | 无已发布草稿；上游简单轨道数检查不足以证明引用完整 |
| J. 用户在剪映手动打开并检查 | NOT_RUN | 没有可打开的测试草稿；尚不能进入 WAITING_USER_CHECK 或 ACCEPTED |

合成素材位于 `tests/synthetic-fixtures/generated/`，包括两段视频、图片、6 秒合成音频和两句中文 SRT；`verification.json` 保存 FFprobe 数据和哈希，`generate.py` 保存生成方法。`edit-plan.json` 是独立计划，未经 MCP 渲染或导入剪映。未自动删除任何测试工程、调用云端或会员素材。
