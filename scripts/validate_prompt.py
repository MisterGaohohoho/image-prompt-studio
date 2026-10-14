#!/usr/bin/env python3
"""Nano Banana 结构化 JSON 提示词校验器。

用法:
    python validate_prompt.py <prompt.json>          # 完整模式：所有字段必填
    python validate_prompt.py <prompt.json> --partial # 部分模式：仅校验已存在字段（如"仅角色"预设）
    python validate_prompt.py -                       # 从 stdin 读取 JSON

校验内容:
    - 必需键是否齐全（完整模式）
    - 各字段值是否为空
    - "审美控制.材质真实度" 必须为字符串数组
    - 嵌套对象层级是否正确

退出码: 0 = 通过, 1 = 存在错误, 2 = 输入无法解析
"""
import json
import sys

# (路径, 说明)；路径以 '.' 分隔，空列表表示顶层字符串字段
REQUIRED_STR_FIELDS = [
    ("风格模式", "顶层画风定调"),
    ("画面气质", "情绪/氛围关键词"),
    ("场景.环境.地点设定", "具体地点"),
    ("场景.环境.光线", "布光术语"),
    ("场景.环境.天气氛围", "季节时间与空气感"),
    ("场景.主体.整体描述", "主体身份与类别"),
    ("场景.主体.外形特征.身材", "体型"),
    ("场景.主体.外形特征.面部", "面容特征"),
    ("场景.主体.外形特征.头发", "发型发色"),
    ("场景.主体.外形特征.眼睛", "瞳色眼神"),
    ("场景.主体.表情与动作.情绪", "情绪词"),
    ("场景.主体.表情与动作.动作", "完整动作链"),
    ("场景.主体.服装.穿着", "配色形制"),
    ("场景.主体.服装.细节", "材质装饰"),
    ("场景.主体.配饰", "点缀物"),
    ("场景.背景.描述", "背景内容"),
    ("场景.背景.景深", "虚化强度"),
    ("相机.机位角度", "视角"),
    ("相机.构图", "景别与取舍"),
    ("相机.镜头特性", "焦段"),
    ("相机.传感器画质", "画质声明"),
    ("审美控制.呈现意图", "成品定位"),
    ("审美控制.色彩风格.整体色调", "主色点缀"),
    ("审美控制.色彩风格.对比度", "明暗风格"),
    ("审美控制.色彩风格.特殊效果", "粒子光效等"),
]

TOP_LEVEL_SECTIONS = ["风格模式", "画面气质", "场景", "相机", "审美控制"]


def get_by_path(data: dict, path: str):
    """按 'a.b.c' 取嵌套值，不存在返回 (False, None)。"""
    node = data
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return False, None
        node = node[key]
    return True, node


def validate(data, partial: bool):
    errors, warnings = [], []

    if not isinstance(data, dict):
        return ["根节点必须是 JSON 对象"], []

    # 顶层小节
    for section in TOP_LEVEL_SECTIONS:
        exists, value = get_by_path(data, section)
        if not exists or value in (None, "", {}, []):
            msg = f"缺少顶层字段: {section}"
            (warnings if partial else errors).append(msg)

    # 必需字符串字段
    for path, desc in REQUIRED_STR_FIELDS:
        exists, value = get_by_path(data, path)
        if not exists:
            if not partial:
                errors.append(f"缺少字段: {path}（{desc}）")
            continue
        if not isinstance(value, str):
            errors.append(f"类型错误: {path} 应为字符串，实际为 {type(value).__name__}")
        elif not value.strip():
            errors.append(f"空值: {path}（{desc}）不能为空")

    # 材质真实度：必须为非空字符串数组
    exists, value = get_by_path(data, "审美控制.材质真实度")
    if exists:
        if not isinstance(value, list):
            errors.append(
                f"类型错误: 审美控制.材质真实度 应为数组，实际为 {type(value).__name__}"
            )
        elif not value:
            errors.append("空值: 审美控制.材质真实度 至少需要 1 条")
        elif not all(isinstance(item, str) and item.strip() for item in value):
            errors.append("审美控制.材质真实度 数组中存在空串或非字符串元素")

    # 层级健全性：场景/相机/审美控制 若存在必须是对象
    for path in ["场景", "场景.环境", "场景.主体", "场景.主体.外形特征",
                 "场景.主体.表情与动作", "场景.主体.服装", "场景.背景",
                 "相机", "审美控制", "审美控制.色彩风格"]:
        exists, value = get_by_path(data, path)
        if exists and not isinstance(value, dict):
            errors.append(f"类型错误: {path} 应为对象，实际为 {type(value).__name__}")

    return errors, warnings


def main():
    args = [a for a in sys.argv[1:]]
    partial = "--partial" in args
    args = [a for a in args if a != "--partial"]

    if len(args) != 1:
        print(__doc__)
        return 2

    src = args[0]
    try:
        raw = sys.stdin.read() if src == "-" else open(src, "r", encoding="utf-8").read()
        data = json.loads(raw)
    except FileNotFoundError:
        print(f"[错误] 文件不存在: {src}")
        return 2
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e}")
        return 2

    errors, warnings = validate(data, partial)

    for w in warnings:
        print(f"[提示] {w}（部分模式跳过）")
    if errors:
        print(f"[失败] 共 {len(errors)} 个问题:")
        for e in errors:
            print(f"  - {e}")
        return 1

    mode = "部分模式" if partial else "完整模式"
    print(f"[通过] {mode}校验通过，结构完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
