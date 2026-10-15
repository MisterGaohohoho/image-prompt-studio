# 生图操作手册（apiz-cli：Nano Banana / GPT-Image 双兼容）

提示词 JSON 就绪后的出图规范。生图通道统一使用 **apiz-cli**；**同一份结构化 JSON 提示词同时兼容 Nano Banana 与 GPT-Image 两个模型家族**，已实测验证（2026-10-14）。

## prompt 组装规则（所有模型通用）

1. 把结构化 JSON 的原文作为 prompt：`json.dumps(data, ensure_ascii=False, indent=2)`。
2. 用户有额外要求时，以 `"\n\n特别要求：<要求内容>"` 形式追加在 JSON 之后。
3. 角色线稿等特殊任务不走 JSON 路线，直接使用 `options-library.md` 末尾的专用提示词。

## 标准命令模板

```bash
apiz generate "$(cat prompt.json)" \
  --model apiz/gpt-image-2.5-flare \
  --aspect-ratio 3:4 \
  --params '{"quality":"low"}' \
  --wait --json
```

- `--aspect-ratio`：竖构图 `3:4`，横构图 `16:9`，方形 `1:1`；参照原图比例或用户要求。
- `--params`：额外参数 JSON 对象，合并进请求体。
- `--wait`：阻塞至任务终态；单张生成通常需数分钟，前台执行注意超时（建议给足 5-10 分钟或后台运行）。
- `--json`：结构化输出，含 `result.images[0].url`（图片直链）、`price`（积分消耗）、`status`。
- **无 `--out` 标志**：用返回的 url 自行下载：`curl -sL -o out.jpg "<url>"`。

## 模型选择表

| 路线 | 模型 ID | 特点 | 适用 |
|---|---|---|---|
| GPT-Image（默认） | `apiz/gpt-image-2.5-flare` | 异步生成 + 参考图编辑；十种比例或自定义 width/height；五档质量；最多 16 张参考图；支持透明背景 | 通用默认路线 |
| GPT-Image（备选） | `apiz/gpt-image-2.5-sunburst` | 同家族备选 | flare 效果不符时切换 |
| Nano Banana | `service-inference/gemini-nano-banana-2.1` | 文生图与参考图编辑同一端点；14 种宽高比（含 1:4/1:8/4:1/8:1 超长比例）；1K/2K/4K 分辨率；最多 14 张参考图；传入 `image_urls` 自动切改图模式，`aspect_ratio=auto` 跟随输入图比例 | 需要 Gemini 画风 / 参考图编辑 / 超长比例 |
| Nano Banana（备选） | `fal-ai/nano-banana-2`、`fal-ai/nano-banana-pro`、`kapon/gemini-3-pro-image-preview` | 同家族其他供货通道 | 主通道不可用时切换 |

实时模型列表：`apiz models list --json | grep image`。

## 质量档位与价格（GPT-Image 路线）

- 五档：`low` / `medium` / `high` / `xhigh` / `max`。
- **默认 `low`**：10 积分/张（0.1 元）；`high` 为 64 积分/张，差 6.4 倍。除非用户点名要高清，否则一律 `low`。
- Nano Banana 路线无质量档参数，分辨率通过 `image_size`（1K/2K/4K）控制。

## 风格参考图（出图必做步骤，不是可选项）

**铁律：只要本次提示词是从参考图分析得来的（路径 A 带图、路径 B 带图），出图时就必须把那张原图作为风格参考一并传入。**否则等于"分析完就丢掉原图"，模型只能靠文字描述猜画风，还原度大幅下降——这是 2026-10-15 修掉的实测 bug。

### 第 1 步 · 本地图转 URL（apiz 只接受 URL，不接本地路径）

```bash
apiz upload "<本地图片路径>" --json
# 返回 { "public_url": "https://cdn-hk.51sux.com/storage/cli-uploads/...", ... }
```

- 取出 `public_url` 备用。已有公网直链时可改用 `apiz transfer "<外部URL>"`（免费镜像进 apiz CDN）。
- 上传产物在 `cli-uploads/` 前缀下，可用 `--folder` 指定其他目录。

### 第 2 步 · 出图时带上参考图（两条路线参数名不同，注意！）

```bash
# GPT-Image 路线：参数名是 reference_image_urls（数组，1-16 张即为图生图）
apiz generate "$(cat prompt.json)" \
  --model apiz/gpt-image-2.5-flare --aspect-ratio 1:1 \
  --params '{"quality":"low","reference_image_urls":["<public_url>"]}' \
  --wait --json

# Nano Banana 路线：参数名是 image_urls（传入即自动进入改图模式，最多 14 张）
apiz generate "$(cat prompt.json)" \
  --model service-inference/gemini-nano-banana-2.1 --aspect-ratio 1:1 \
  --params '{"image_urls":["<public_url>"]}' \
  --wait --json
```

**实测证伪（2026-10-15，别再踩）**：

| 传法 | GPT-Image flare | Nano Banana 2.1 |
|---|---|---|
| `--image-url "<url>"`（CLI 旗标） | ❌ HTTP 400 不支持 `image_url` | 未采用 |
| `--params '{"image_urls":[…]}'` | ❌ HTTP 400 不支持 `image_urls` | ✅ 正确参数 |
| `--params '{"reference_image_urls":[…]}'` | ✅ **正确参数**（1-16 张，省略即文生图） | 未验证 |

- 多张参考图：数组里并列多个 URL。
- Nano Banana 的 `aspect_ratio=auto` 会跟随输入图比例；**要按 JSON 构图走时显式指定 `--aspect-ratio`**。
- **风格参考 vs 改图**：两者共用同一参数。想"借画风、换内容"时靠 JSON 提示词的完整描述压过原图内容；想"在原图上改"时 JSON 只写改动点即可。需要彻底分清时，在 JSON 后追加 `"\n\n特别要求：仅参考其画风与色彩基调，画面内容严格以本 JSON 描述为准"`。
- **带参考图实测收益**：同一份「诸葛亮坐大象」JSON，无参考图版羽扇/太极纹等细节易丢失；带参考图版画风与参考图高度一致，且坐骑继承了原图同款滑稽圆眼——**风格参考显著提升还原度**（对比图见 README 示例 2）。

## 已知坑（实测）

1. **参数兼容性**：GPT-Image 路线的 `image_size` / `resolution` / `num_images` / `n` / `background` / `image` / `images` / `image_url` / `image_urls` 均报 HTTP 400；尺寸只用 `--aspect-ratio`（或 `size` 1K/2K/4K、`width`+`height`），质量只用 `quality`，参考图只用 `reference_image_urls`。其参数白名单实测仅：`aspect_ratio`、`quality`、`size`、`width`、`height`、`reference_image_urls`、`transparent_background` 等少量键。
2. **生成耗时**：单张 3-7 分钟不等；`--wait` 前台执行易触到工具超时，长任务用后台运行（结果重定向到文件）。
3. **输出为 JPEG**：项目若要求 PNG，用 PIL 转换（`Image.open(...).save(out.png)`）。
4. **余额闸门**：欠费时所有模型返回 HTTP 429 余额不足。出图前 `apiz account balance` 确认（1 积分 = 0.01 元）。
5. **批量生图**：串行或小并发执行，每张一个任务，避免输出相互覆盖；每张精确控制下载落盘。
6. **密钥安全**：API key 只走 apiz 配置（profile / env），不写进任何脚本、日志或交付文件。

## 实测记录（2026-10-14）

- 测试图：`E:\三国seedance\_3_LLHAN_来自小红书网页版.jpg`（911×954，三国题材夸张讽刺漫画，白底骑驴武将）。
- 流程：运行时 agent 读图分析 → 生成结构化 JSON（`assets/examples/prompt.json`）→ 校验通过 → apiz-cli 双模型出图。
- GPT-Image flare（quality=low, 1:1）：成功，1024×1024 PNG，10 积分。
- Nano Banana 2.1（1:1）：成功，1024×1024 JPEG，19 积分。
- 两条路线均正确还原粗黑描边漫画风、狂笑武将、双矛、张字大旗与滑稽坐骑；纯白背景与方形构图准确保留。
- 注：单张生成耗时 8-9 分钟（本次两模型并行亦如此），务必后台运行。

### 追加实测：路径 B 最小化修改稿出图（2026-10-14）

- 修改指令：「改成 诸葛亮坐在大象」，输入 `assets/examples/prompt.json`，输出 `assets/examples/prompt-modified.json`；字段级 diff 显示 26 个叶子字段中仅 11 个改动、15 个逐字冻结。
- GPT-Image flare（quality=low, 1:1）：成功，1024×1024 JPEG，**3m11s**，10 积分。
- Nano Banana 2.1（1:1）：成功，1024×1024 JPEG，**8m28s**，19 积分（返回体 `width`/`height` 为 `null`，需下载后实测尺寸）。
- 两模型均保住原 JSON 的漫画风与纯白方形构图，主体准确换为羽扇纶巾、端坐巨象的诸葛亮——**证明只改主体字段不会导致画风漂移**。

### 追加实测：带风格参考图出图（2026-10-15，修复"出图丢参考图"bug）

- **bug**：此前路径 A/B 分析完参考图后，出图命令没有把原图传回去，模型只能靠文字猜画风。修复后"带参考图"成为出图硬性步骤。
- **本地转 URL**：`apiz upload "<本地图片>" --json` → `public_url`（实测上传原图 148KB，秒回）。
- **flare 实测**：`--params '{"quality":"low","reference_image_urls":["<url>"]}'` ✅ 成功，1024×1024 PNG，10 积分，**1m42s**。画风与参考图高度一致（粗描边+平涂+滑稽圆眼坐骑+撕裂红旗+绿金鞍毯），细节还原明显优于无参考图版。
- **探针记录**：flare 对 `image_url`（CLI 旗标 `--image-url`）、`image_urls`、`images`、`image`、`reference_images`、`input_images`、`image_reference` 全部返回 400 不支持；**唯一正确的参数名是 `reference_image_urls`**（用户指出后验证通过）。
- **NB 路线实测**：`image_urls` 参数正确；但 `service-inference/gemini-nano-banana-2.1` 连续两次**上游 502**（Gemini 上游故障，`apiz tasks get <task_id>` 查到 `qimg Gemini 图片上游 HTTP 502`）；切备选 `fal-ai/nano-banana-pro`（成功率 96%）✅ 成功，1024×1024 PNG，**3m01s，60 积分**（比主通道 19 积分贵 3 倍，主通道恢复后优先主通道）。备选 `fal-ai/nano-banana-2` 成功率仅 12.2%，不推荐。
- **CLI 等待坑**：`--wait` 默认等待上限 10 分钟（`--wait-timeout` 可调，最大实测 15m 可用）；超时后任务仍在服务端继续，用 `apiz tasks wait <task_id> --json` 续接，不要盲目重跑（重跑=重复扣费）。
