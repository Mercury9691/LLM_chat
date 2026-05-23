import json
import re

import requests

from app_modules.config import OLLAMA_BASE_URL, TOP_K
from app_modules.helpers import get_base64_image


PROMPT_AGENT_SYSTEM_PROMPT = """You are an expert image prompt rewriting engine for image generation models.

Your task is to transform a user's raw idea into one clear, detailed, production-ready English image prompt.

Goals:
- Output one natural English prompt paragraph, not keyword soup.
- Make the visual subject, composition, action, location, lighting, style, and technical qualities explicit.
- Resolve hidden knowledge when needed. If the user references a poem, historical event, cultural symbol, famous person, landmark, formula, or text layout, expand it into visible, concrete details.
- If text must appear inside the image, preserve the exact text in quotes and describe placement, style, and material.
- Turn abstract ideas into visible scenes, symbols, mood, and composition.
- Keep the result self-contained so the image model does not need to infer missing context.

Output JSON only:
{"prompt": "final English prompt", "reasoning": "short Chinese explanation", "resolved_knowledge": "short Chinese note about resolved hidden knowledge, or 无"}"""


def _is_mistral_model(model_name):
    return "mistral" in str(model_name or "").lower()


def _build_vllm_request_options(model_name, enable_thinking=False, sampling_params=None):
    sampling_params = sampling_params or {"temperature": 0.7, "top_p": 0.9, "top_k": TOP_K}
    if _is_mistral_model(model_name):
        reasoning_effort = "high" if enable_thinking else "none"
        return {
            "temperature": 0.7 if enable_thinking else 0.1,
            "top_p": 0.95 if enable_thinking else None,
            "extra_body": {"reasoning_effort": reasoning_effort},
        }
    return {
        "temperature": sampling_params.get('temperature', 0.7),
        "top_p": sampling_params.get('top_p', 0.9),
        "extra_body": {
            "top_k": sampling_params.get('top_k', TOP_K),
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
        },
    }


def _extract_json_block(text):
    depth = 0
    start = None
    in_string = False
    escape_next = False
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return text[start:i + 1]
    return None


def _fix_unescaped_newlines(text):
    out = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            out.append(ch)
            escape_next = False
            continue
        if ch == "\\" and in_string:
            out.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
            continue
        if in_string and ch == "\n":
            out.append("\\n")
            continue
        if in_string and ch == "\r":
            continue
        out.append(ch)
    return "".join(out)


def parse_prompt_agent_json(text):
    text = (text or "").strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    block = _extract_json_block(text) or text
    for candidate in (block, _fix_unescaped_newlines(block)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"Failed to parse JSON from model output: {text[:500]}")


def _wrap_prompt_agent_result(raw, user_input):
    try:
        result = parse_prompt_agent_json(raw)
        prompt = result.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Missing prompt field")
        return {
            "prompt": prompt.strip(),
            "reasoning": str(result.get("reasoning") or "已根据画面主体、构图、风格和细节要求完成提示词重写。").strip(),
            "resolved_knowledge": str(result.get("resolved_knowledge") or "无").strip(),
            "raw": raw,
        }
    except Exception:
        return {
            "prompt": f"{user_input}, highly detailed, masterpiece, best quality, sharp focus",
            "reasoning": "解析优化结果失败，已回退为基于原始描述的增强提示词。",
            "resolved_knowledge": "无",
            "raw": raw,
        }


def rewrite_prompt_ollama(user_input, model_name, sampling_params=None):
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": PROMPT_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        "think": False,
        "stream": False,
    }
    if sampling_params:
        payload["options"] = {
            "temperature": sampling_params.get('temperature', 0.7),
            "top_p": sampling_params.get('top_p', 0.9),
            "top_k": sampling_params.get('top_k', 40)
        }
    response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()
    raw = data.get('message', {}).get('content', '') or ''
    return _wrap_prompt_agent_result(raw, user_input)


def rewrite_prompt_vllm(client, user_input, model_name, enable_thinking=False, sampling_params=None):
    if sampling_params is None:
        sampling_params = {"temperature": 0.7, "top_p": 0.9, "top_k": TOP_K}
    request_options = _build_vllm_request_options(model_name, enable_thinking, sampling_params)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": PROMPT_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        temperature=request_options["temperature"],
        top_p=request_options["top_p"],
        extra_body=request_options["extra_body"],
    )
    raw = response.choices[0].message.content or ""
    return _wrap_prompt_agent_result(raw, user_input)


def generate_ollama(messages, model_name, sampling_params=None):
    ollama_msgs = []
    for m in messages:
        msg_obj = {"role": m['role'], "content": m['text']}
        if m.get('media_path'):
            msg_obj["images"] = [get_base64_image(m['media_path'])]
        ollama_msgs.append(msg_obj)

    payload = {"model": model_name, "messages": ollama_msgs, "think": False, "stream": True}
    if sampling_params:
        payload["options"] = {
            "temperature": sampling_params.get('temperature', 0.7),
            "top_p": sampling_params.get('top_p', 0.9),
            "top_k": sampling_params.get('top_k', 40)
        }
    try:
        r = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, stream=True)
        for line in r.iter_lines():
            if line:
                chunk = json.loads(line)
                content = chunk.get('message', {}).get('content', '')
                yield content
                if chunk.get('done'): break
    except Exception as e:
        yield f"Ollama Error: {str(e)}"


def generate_vllm(client, messages, model_name, enable_thinking=False, sampling_params=None):
    openai_msgs = []
    last_idx = -1
    for i, m in enumerate(messages):
        if m.get('media_url'): last_idx = i

    for i, m in enumerate(messages):
        role, text = m['role'], m['text']
        if i == last_idx and m.get('media_url'):
            content = [{"type": "text", "text": text}]
            m_url, m_type = m['media_url'], m.get('media_type', 'image')
            key = "image_url" if m_type == "image" else "video_url"
            # In a real setup, we might pass the full URL or let vLLM fetch it.
            # Assuming VLLM can access the media_url or we pass base64
            # We will use base64 to be safe.
            if m.get('media_path'):
                b64 = get_base64_image(m['media_path'])
                data_url = f"data:image/jpeg;base64,{b64}"
                content.insert(0, {key: {"url": data_url}, "type": key})
            openai_msgs.append({"role": role, "content": content})
        else:
            openai_msgs.append({"role": role, "content": text})

    try:
        if sampling_params is None:
            sampling_params = {"temperature": 0.7, "top_p": 0.9, "top_k": TOP_K}
        request_options = _build_vllm_request_options(model_name, enable_thinking, sampling_params)
        stream = client.chat.completions.create(
            model=model_name,
            messages=openai_msgs,
            temperature=request_options["temperature"],
            top_p=request_options["top_p"],
            stream=True,
            extra_body=request_options["extra_body"]
        )
        in_reasoning = False
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            
            # Safely extract reasoning_content (handles different openai library versions)
            reasoning = getattr(delta, 'reasoning_content', None)
            if reasoning is None and hasattr(delta, 'model_extra') and delta.model_extra:
                reasoning = delta.model_extra.get('reasoning_content')
                
            content = getattr(delta, 'content', None)
            
            if reasoning is not None and reasoning != "":
                if not in_reasoning:
                    yield "<think>\n"
                    in_reasoning = True
                yield reasoning
                
            if content is not None and content != "":
                if in_reasoning:
                    yield "\n</think>\n"
                    in_reasoning = False
                yield content
                
        if in_reasoning:
            yield "\n</think>\n"
    except Exception as e:
        yield f"vLLM Error: {str(e)}"

