"""LLM 摘要：DeepSeek（OpenAI 兼容接口）。失败自动降级，绝不阻塞主流程。只依赖标准库。"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from .config import env
from .feed import Item

API_URL = env("LLM_BASE_URL", "https://api.deepseek.com/chat/completions")
MODEL = env("LLM_MODEL", "deepseek-chat")

SYSTEM_PROMPT = """你是一个中文科技新闻编辑，为读者写每日简报。
规则：
1. 每条输出一行，格式严格为：编号|一句话摘要|为什么值得看
2. 摘要不超过 45 个汉字，说明"发生了什么"，不要用"本文介绍了"这类空话
3. "为什么值得看"不超过 25 个汉字，说清影响或变化
4. 只能依据我给的标题和摘要，禁止编造事实、数字、人名
5. 如果信息不足以判断，第二段写"信息有限"
6. 不要输出编号以外的任何解释、开场白、结尾语"""


def _build_user_prompt(items: list[Item]) -> str:
    lines = []
    for idx, it in enumerate(items, 1):
        summary = (it.summary or "")[:280]
        lines.append(f"{idx}. 标题：{it.title}\n   摘要：{summary}\n   来源：{it.source}")
    return "请为下列新闻各写一条简报：\n\n" + "\n\n".join(lines)


def _post(payload: dict, api_key: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_reply(text: str, count: int) -> dict[int, tuple[str, str]]:
    """把 '1|摘要|理由' 解析成 {1: (摘要, 理由)}，容忍模型加粗/多余空格。"""
    result: dict[int, tuple[str, str]] = {}
    for line in text.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        m = re.match(r"^(\d+)\s*[|｜:：.)、]\s*(.+)$", line)
        if not m:
            continue
        idx = int(m.group(1))
        if not (1 <= idx <= count):
            continue
        body = m.group(2)
        parts = re.split(r"[|｜]", body, maxsplit=1)
        summary = parts[0].strip()
        why = parts[1].strip() if len(parts) > 1 else ""
        if summary:
            result[idx] = (summary[:120], why[:80])
    return result


def _fallback(item: Item) -> tuple[str, str]:
    """AI 不可用时的降级摘要：取原文首句；噪音内容则留空，不硬凑。"""
    text = (item.summary or "").strip()
    if not text or len(text) < 12:
        return ("", "")
    text = re.split(r"[。！？.!?]\s*", text)[0].strip()
    if len(text) < 10:
        return ("", "")
    return (text[:80], "")


def summarize(items: list[Item]) -> list[Item]:
    """就地写入 item.extra['brief'] 和 item.extra['why']。任何异常都降级。"""
    if not items:
        return items

    api_key = env("LLM_API_KEY") or env("DEEPSEEK_API_KEY") or env("OPENAI_API_KEY")
    if not api_key:
        print("  [info] 未配置 LLM_API_KEY，使用降级摘要（取原文首句）")
        for it in items:
            it.extra["brief"], it.extra["why"] = _fallback(it)
        return items

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(items)},
        ],
        "temperature": 0.3,
        "max_tokens": 1200,
    }

    for attempt in range(2):
        try:
            data = _post(payload, api_key)
            content = data["choices"][0]["message"]["content"]
            parsed = _parse_reply(content, len(items))
            if len(parsed) >= max(1, len(items) // 2):
                for idx, it in enumerate(items, 1):
                    it.extra["brief"], it.extra["why"] = parsed.get(idx, _fallback(it))
                print(f"  [ok] AI 摘要完成 {len(parsed)}/{len(items)} 条")
                return items
            print(f"  [warn] AI 返回格式异常（解析到 {len(parsed)} 条），重试")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "ignore")[:200]
            except Exception:
                pass
            print(f"  [warn] LLM HTTP {exc.code}: {body}")
            if exc.code in (401, 403):
                break
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] LLM 调用失败: {exc}")

    print("  [info] AI 摘要失败，降级为原文首句")
    for it in items:
        it.extra["brief"], it.extra["why"] = _fallback(it)
    return items
