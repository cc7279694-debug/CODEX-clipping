# ClipPlan V1 数据契约（Phase 4A）

本契约用于新工程的保守剪辑计划；数据不是对讲话、笑声或叙事停顿安全性的证明。自动验证、支持的 OpenFilm 子集和实际结果以 [Phase 4A 报告](evidence/PHASE4A-REPORT.md) 为准。未经审核的决定不得导出为正式片段；本阶段只用合成素材。

## JSON 根对象

| 字段 | 含义 |
| --- | --- |
| `schema_version` | 整数 `1`。 |
| `revision` | 非负修订编号；初始 `0`，审核动作产生新修订。 |
| `history` | 审核事件数组；初始空。事件记录版本、片段、动作及前后状态；撤销引用被撤销的修订。记录可编辑且不带签名，并不证明人类确已完成听审。 |
| `output` | 输出工程参数：`width`、`height`、`fps`、`duration`；帧率和尺寸不能只由文件名推断，时间均为秒。 |
| `sources` | 明确授权的源素材清单。 |
| `tracks` | 时间线轨道，顺序及叠放语义由适配器按 OpenFilm 官方支持能力处理。 |
| `clips` | 映射到来源与轨道的片段，时间以源秒和时间线秒分别记录。 |

## 来源、轨道与片段

| 对象 | 字段 | 约束/解释 |
| --- | --- | --- |
| 来源 | `source_id` | 稳定唯一 ID；引用缺失或重复必须拒绝。 |
| 来源 | `relative_path` | 相对于显式授权素材根目录的路径；禁止绝对路径、`..` 及越过授权根的链接。公开仓库中不得出现私人绝对路径。 |
| 来源 | `sha256` | 小写 SHA-256；计划与实际素材逐项匹配，处理前后检查源哈希。哈希一致只能证明字节一致。 |
| 来源 | `duration_seconds`, `media_type` | 来源时长与 `video` / `audio` 类型；实际时长和音视频流由 FFprobe 核对，不信任调用方自填数值。 |
| 轨道 | `track_id`, `media_type`, `role` | 唯一轨道 ID、媒体类型与用途，当前用途为 `main`、`broll`、`voice`、`music`；引用、类型和角色需匹配。 |
| 片段 | `clip_id`, `source_id`, `track_id` | 唯一片段 ID 和已有来源/轨道引用。ID 使用以 ASCII 字母开头、其后为字母数字/下划线/连字符的安全形式，最长 64 字符；拒绝 Windows 保留设备名称，按大小写不敏感去重。 |
| 片段 | `source_start`, `source_end` | 源素材左闭右开区间 `[source_start, source_end)`，以秒为单位，起点 ≥ 0、终点大于起点且不超过经过核对的源时长。 |
| 片段 | `timeline_start`, `timeline_duration` | 成片时间线左闭右开区间 `[timeline_start, timeline_start + timeline_duration)`，以秒为单位。不得超过工程时长。同一轨道的片段不得重叠。 |
| 片段 | `speed`, `volume`, `muted` | 当前保守实现只允许 `speed=1`、`volume=1`；`main` / `voice` / `music` 不得静音，`broll` 必须静音。其他设置不声称支持；音视频是否实际保留须到 Studio 播放验收。 |
| 片段 | `media_type`, `role`, `evidence` | `media_type` 为 `video` 或 `audio`，必须与轨道类型一致；`role` 与轨道用途一致，区分 main、B-roll、voice、music；`evidence` 为非空来源/决策证据引用。证据字符串和角色不认证内容或音轨安全。 |
| 片段 | `review_status` | `pending`（待审）、`accepted`（接受）、`rejected`（拒绝）；非 `accepted` 的片段不可导出。 |

所有时间、速度、音量必须是有限数字，布尔值不能冒充数字。不能有负时间、零长度、超出范围的片段。同一文件不能被作为多个来源重复登记，所有来源和轨道都必须被实际片段引用。模型校验阶段保留输入时间精度，`timeline_duration = (source_end - source_start) / speed`；同轨交叠比较采用十进制，避免二进制浮点误差把相接片段误认为交叠。导出时必须符合本机 OpenFilm 支持的精度；不能把改变边界、丢失声音或产生重叠的舍入当成合法输出。对不能安全映射的片段直接拒绝。

B-roll 必须覆盖有主画面的时间段并置于上层、静音；若内含原声的主视频与独立 `voice` 轨时间重叠，当前版本为避免重复人声而拒绝。不同轨道的 main 之间、voice 之间发生时间重叠时也拒绝；分时排列可以。即使静态规则通过，音轨听感仍需用户在 Studio 中确认，无法证明已保留每一处讲话。

## 审核与修订

每个片段初始默认待审；明确审核后可接受或拒绝。`review_clip(plan, clip_id, action)` 产生计划副本，不改旧版；`accept` / `reject` 记 `from_status` 与 `to_status`，`undo` 引用待撤销的 `target_revision` 并恢复相应状态。事件包含 `revision`、`clip_id`、`action`、`from_status`、`to_status`，并绑定完整计划的非审核状态内容摘要；更改来源、音画属性、源时间、时间线或输出参数会使旧审核无效。撤销只改变计划的状态，不更改素材，也不证明听审发生；篡改的历史和伪造的人工声明不能作为安全证据。审核需覆盖每个导出片段，任何未接受片段须阻止发布。

事件中的 `plan_sha256` 使用 UTF-8 规范 JSON（`sort_keys=True`、`separators=(',', ':')`、`ensure_ascii=True`、`allow_nan=False`）计算：包含完整计划，排除根对象 `revision`、`history` 及每个片段的 `review_status`。因此额外字段也被绑定；计划内容变更需建立新的待审计划并重新审核。摘要用于检测意外变更，不能认证审核者身份或防止能够重写计划的人伪造记录。

## 来源到时间线的例子

假设测试视频 `A` 的源区间 `[0,7.5)` 对应成片 `[0,7.5)`，测试视频 `B` 的源区间 `[0,7.5)` 对应成片 `[7.5,15)`；测试音频从源 `[0,15)` 映射至独立音轨 `[0,15)`。这只是时间坐标的示意，不是实际素材或播放已通过的证据。若视频含音频，必须明确处理原声与独立音轨的关系，避免无意重复、静音或中断。

## 新工程与验证边界

`validate_clip_plan(plan, source_root, ffprobe, require_approved=...)` 的意图是校验计划与本地素材并返回来源映射；生成器必须在受控独立目录创建新工程，复制素材到相对资源路径，保留来源与哈希，并在写入前后校验，绝不覆盖现有项目。`create_openfilm_project` 必须显式指定 `allowed_output_root`：工程目标只能是该已存在输出根下的直接新子目录，且源根与输出根不能相同或互相嵌套。`film.html` 的媒体片段 `#t=` 是源区间，`at=` 是时间线位置；输出和轨道细节以本机 OpenFilm 官方格式及适配器已验证子集为准。仅凭 JSON、HTML 静态检查或真实文件存在，不能证明 Studio 中已打开、音画正确或可以保存编辑。

当前生成器把 `fps` 保存在 ClipPlan 中，但本机 OpenFilm 工程的帧率写入方式尚未验证，不能据此声称生成工程实际使用该帧率。生成项目只支持已确认的简单音视频片段子集；复杂转场、字幕、修改现有项目及非标准音画处理均不在本阶段能力内。
