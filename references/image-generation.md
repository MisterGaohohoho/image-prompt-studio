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

## 参考图（图生图 / 改图）

- 单张参考图：`--image-url "<图片URL>"`。
- 多张参考图：通过 `--params '{"image_urls": ["url1","url2"]}'` 传入（Nano Banana 路线提供 image_urls 即自动进入改图模式）。
- 本地图片需先转为可访问 URL，或以 base64 data URI 形式传入（视通道支持）。
- 参考图 + 修改指令的组合，配合路径 B 的最小化修改提示词使用。

## 已知坑（实测）

1. **参数兼容性**：GPT-Image 路线的 `image_size` / `resolution` / `num_images` 参数会报 HTTP 400 不支持的参数；尺寸只用 `--aspect-ratio`，额外参数只放 `quality`。
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
