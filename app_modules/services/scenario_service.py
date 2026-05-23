import datetime
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional

import requests

from app_modules.config import PROJECTS_DIR
import utils


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def get_scenario_dir(project: str) -> str:
    pj_path = utils.ensure_project_structure(PROJECTS_DIR, project)
    data_dir = os.path.join(pj_path, "resource", "ai_scenario")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_db_path(project: str) -> str:
    return os.path.join(get_scenario_dir(project), "scenario.db")


def connect(project: str) -> sqlite3.Connection:
    init_db(project)
    conn = sqlite3.connect(get_db_path(project))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_connection(project: str) -> Iterable[sqlite3.Connection]:
    conn = connect(project)
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


def init_db(project: str) -> None:
    db_path = get_db_path(project)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            background TEXT NOT NULL DEFAULT '',
            scene TEXT NOT NULL DEFAULT '',
            initial_state TEXT NOT NULL DEFAULT '',
            main_story TEXT NOT NULL DEFAULT '',
            compressed_summary TEXT NOT NULL DEFAULT '',
            recent_story_for_context TEXT NOT NULL DEFAULT '',
            current_turn INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            public_info TEXT NOT NULL DEFAULT '',
            goal_prompt TEXT NOT NULL DEFAULT '',
            is_human INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            turn_no INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'collecting',
            pending_resolution TEXT NOT NULL DEFAULT '',
            final_resolution TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(game_id, turn_no),
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            turn_no INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            role_name TEXT NOT NULL,
            speech TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'ai',
            raw_output TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(game_id, turn_no, role_id),
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


def list_games(project: str) -> List[Dict[str, Any]]:
    with db_connection(project) as db:
        rows = db.execute("SELECT * FROM games ORDER BY updated_at DESC, id DESC").fetchall()
        return [row_to_dict(row) for row in rows]


def create_game(project: str, title: str) -> int:
    ts = now_iso()
    with db_connection(project) as db:
        cur = db.execute(
            """
            INSERT INTO games
            (title, background, scene, initial_state, main_story, created_at, updated_at)
            VALUES (?, '', '', '', '', ?, ?)
            """,
            (title or "未命名剧本", ts, ts),
        )
        db.commit()
        return int(cur.lastrowid)


def fetch_game(project: str, game_id: int) -> Optional[Dict[str, Any]]:
    with db_connection(project) as db:
        row = db.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return row_to_dict(row) if row else None


def fetch_roles(project: str, game_id: int) -> List[Dict[str, Any]]:
    with db_connection(project) as db:
        rows = db.execute(
            """
            SELECT * FROM roles
            WHERE game_id = ? AND is_active = 1
            ORDER BY sort_order ASC, id ASC
            """,
            (game_id,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]


def fetch_turn(project: str, game_id: int, turn_no: int) -> Dict[str, Any]:
    with db_connection(project) as db:
        row = db.execute(
            "SELECT * FROM turns WHERE game_id = ? AND turn_no = ?",
            (game_id, turn_no),
        ).fetchone()
        if row:
            return row_to_dict(row)

        ts = now_iso()
        db.execute(
            """
            INSERT INTO turns (game_id, turn_no, status, created_at, updated_at)
            VALUES (?, ?, 'collecting', ?, ?)
            """,
            (game_id, turn_no, ts, ts),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM turns WHERE game_id = ? AND turn_no = ?",
            (game_id, turn_no),
        ).fetchone()
        return row_to_dict(row)


def fetch_actions(project: str, game_id: int, turn_no: int) -> List[Dict[str, Any]]:
    with db_connection(project) as db:
        rows = db.execute(
            """
            SELECT * FROM actions
            WHERE game_id = ? AND turn_no = ?
            ORDER BY id ASC
            """,
            (game_id, turn_no),
        ).fetchall()
        return [row_to_dict(row) for row in rows]


def build_recent_resolution_context(project: str, game_id: int, current_turn: int) -> str:
    with db_connection(project) as db:
        rows = db.execute(
            """
            SELECT turn_no, pending_resolution, final_resolution
            FROM turns
            WHERE game_id = ? AND turn_no < ?
            ORDER BY turn_no DESC
            LIMIT 2
            """,
            (game_id, current_turn),
        ).fetchall()

    blocks = []
    for row in reversed(rows):
        item = row_to_dict(row)
        resolution = strip_think_artifacts(item.get("pending_resolution") or "").strip()
        if not resolution:
            resolution = strip_think_artifacts(item.get("final_resolution") or "").strip()
        if not resolution:
            continue
        blocks.append(f"【第 {item['turn_no']} 回合管理员结算】\n{resolution}")
    return "\n\n".join(blocks)


def build_roleplay_context(game: Dict[str, Any]) -> str:
    resolution_context = strip_think_artifacts(game.get("recent_resolution_context") or "").strip()
    if resolution_context:
        return resolution_context
    return build_model_story_context(game)


def get_game_state(project: str, game_id: int) -> Optional[Dict[str, Any]]:
    game = fetch_game(project, game_id)
    if not game:
        return None
    turn = fetch_turn(project, game_id, game["current_turn"])
    game["recent_resolution_context"] = build_recent_resolution_context(project, game_id, game["current_turn"])
    model_context = build_roleplay_context(game)
    main_story = game.get("main_story", "")
    return {
        "game": game,
        "roles": fetch_roles(project, game_id),
        "turn": turn,
        "actions": fetch_actions(project, game_id, game["current_turn"]),
        "model_context_preview": model_context,
        "main_story_preview": main_story,
        "token_counts": {
            "main_story": estimate_text_tokens(main_story),
            "model_context": estimate_text_tokens(model_context),
        },
    }


def update_game(project: str, game_id: int, data: Dict[str, Any]) -> bool:
    game = fetch_game(project, game_id)
    if not game:
        return False
    title = data.get("title", game["title"])
    background = data.get("background", game["background"])
    scene = data.get("scene", game["scene"])
    initial_state = data.get("initial_state", game["initial_state"])
    main_story = data.get("main_story")
    if main_story is None:
        main_story = game["main_story"] or (f"【初始状态】\n{initial_state.strip()}" if initial_state else "")

    with db_connection(project) as db:
        db.execute(
            """
            UPDATE games
            SET title = ?, background = ?, scene = ?, initial_state = ?,
                main_story = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, background, scene, initial_state, main_story, now_iso(), game_id),
        )
        db.commit()
    return True


def save_roles(project: str, game_id: int, roles: List[Dict[str, Any]]) -> None:
    ts = now_iso()
    with db_connection(project) as db:
        db.execute("DELETE FROM roles WHERE game_id = ?", (game_id,))
        for idx, role in enumerate(roles):
            name = (role.get("name") or "").strip()
            if not name:
                continue
            db.execute(
                """
                INSERT INTO roles
                (game_id, name, public_info, goal_prompt, is_human, is_active,
                 sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    game_id,
                    name,
                    role.get("public_info", ""),
                    role.get("goal_prompt", ""),
                    1 if role.get("is_human") else 0,
                    idx,
                    ts,
                    ts,
                ),
            )
        db.commit()


def reorder_roles(project: str, game_id: int, ordered_role_ids: List[Any]) -> bool:
    current_roles = fetch_roles(project, game_id)
    if not current_roles:
        return False

    role_map = {int(role["id"]): role for role in current_roles}
    normalized_ids: List[int] = []
    for raw_id in ordered_role_ids or []:
        try:
            role_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if role_id in role_map and role_id not in normalized_ids:
            normalized_ids.append(role_id)

    remaining_ids = [int(role["id"]) for role in current_roles if int(role["id"]) not in normalized_ids]
    final_ids = normalized_ids + remaining_ids
    ts = now_iso()

    with db_connection(project) as db:
        for idx, role_id in enumerate(final_ids):
            db.execute(
                """
                UPDATE roles
                SET sort_order = ?, updated_at = ?
                WHERE game_id = ? AND id = ?
                """,
                (idx, ts, game_id, role_id),
            )
        db.commit()
    return True


def start_game(project: str, game_id: int) -> bool:
    game = fetch_game(project, game_id)
    if not game:
        return False
    main_story = game["main_story"] or f"【初始状态】\n{game.get('initial_state', '').strip()}"
    with db_connection(project) as db:
        db.execute(
            """
            UPDATE games
            SET status = 'running', current_turn = 1, main_story = ?, updated_at = ?
            WHERE id = ?
            """,
            (main_story, now_iso(), game_id),
        )
        db.commit()
    fetch_turn(project, game_id, 1)
    return True


def delete_game(project: str, game_id: int) -> None:
    with db_connection(project) as db:
        db.execute("DELETE FROM actions WHERE game_id = ?", (game_id,))
        db.execute("DELETE FROM turns WHERE game_id = ?", (game_id,))
        db.execute("DELETE FROM roles WHERE game_id = ?", (game_id,))
        db.execute("DELETE FROM games WHERE id = ?", (game_id,))
        db.commit()


def submit_human_action(project: str, game_id: int, data: Dict[str, Any]) -> bool:
    game = fetch_game(project, game_id)
    if not game:
        return False
    role_id = int(data.get("role_id"))
    with db_connection(project) as db:
        role = db.execute(
            "SELECT * FROM roles WHERE id = ? AND game_id = ?",
            (role_id, game_id),
        ).fetchone()
        if not role:
            return False
        ts = now_iso()
        db.execute(
            """
            INSERT OR REPLACE INTO actions
            (game_id, turn_no, role_id, role_name, speech, action, source,
             raw_output, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'human', '', ?, ?)
            """,
            (
                game_id,
                game["current_turn"],
                role_id,
                role["name"],
                data.get("speech", ""),
                data.get("action", ""),
                ts,
                ts,
            ),
        )
        db.commit()
    return True


def commit_turn(project: str, game_id: int, final_resolution: str) -> bool:
    final_resolution = strip_think_artifacts(final_resolution or "").strip()
    game = fetch_game(project, game_id)
    if not game or not final_resolution:
        return False
    turn_no = game["current_turn"]
    append_text = f"\n\n【第 {turn_no} 回合】\n{final_resolution}"
    new_main_story = (game["main_story"] or "") + append_text
    recent_story_for_context = new_main_story[-6000:]
    with db_connection(project) as db:
        db.execute(
            """
            UPDATE turns
            SET status = 'committed',
                final_resolution = ?,
                updated_at = ?
            WHERE game_id = ? AND turn_no = ?
            """,
            (final_resolution, now_iso(), game_id, turn_no),
        )
        db.execute(
            """
            UPDATE games
            SET main_story = ?,
                recent_story_for_context = ?,
                current_turn = current_turn + 1,
                updated_at = ?
            WHERE id = ?
            """,
            (new_main_story, recent_story_for_context, now_iso(), game_id),
        )
        db.commit()
    updated = fetch_game(project, game_id)
    fetch_turn(project, game_id, updated["current_turn"])
    return True


def clear_summary(project: str, game_id: int) -> None:
    with db_connection(project) as db:
        db.execute(
            """
            UPDATE games
            SET compressed_summary = '',
                recent_story_for_context = '',
                updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), game_id),
        )
        db.commit()


def reset_game_progress(project: str, game_id: int) -> bool:
    game = fetch_game(project, game_id)
    if not game:
        return False
    main_story = game["main_story"] or f"銆愬垵濮嬬姸鎬併€慭n{game.get('initial_state', '').strip()}"
    ts = now_iso()
    with db_connection(project) as db:
        db.execute("DELETE FROM actions WHERE game_id = ?", (game_id,))
        db.execute("DELETE FROM turns WHERE game_id = ?", (game_id,))
        db.execute(
            """
            UPDATE games
            SET status = 'running',
                current_turn = 1,
                main_story = ?,
                compressed_summary = '',
                recent_story_for_context = '',
                updated_at = ?
            WHERE id = ?
            """,
            ('', ts, game_id),
        )
        db.execute(
            """
            INSERT INTO turns (game_id, turn_no, status, pending_resolution, final_resolution, created_at, updated_at)
            VALUES (?, 1, 'collecting', '', '', ?, ?)
            """,
            (game_id, ts, ts),
        )
        db.commit()
    return True


def clear_current_turn_board(project: str, game_id: int) -> bool:
    game = fetch_game(project, game_id)
    if not game:
        return False
    turn_no = game["current_turn"]
    ts = now_iso()
    with db_connection(project) as db:
        db.execute(
            "DELETE FROM actions WHERE game_id = ? AND turn_no = ?",
            (game_id, turn_no),
        )
        db.execute(
            """
            UPDATE turns
            SET pending_resolution = '',
                final_resolution = '',
                updated_at = ?
            WHERE game_id = ? AND turn_no = ?
            """,
            (ts, game_id, turn_no),
        )
        db.execute(
            """
            UPDATE games
            SET updated_at = ?
            WHERE id = ?
            """,
            (ts, game_id),
        )
        db.commit()
    fetch_turn(project, game_id, turn_no)
    return True


def strip_think_artifacts(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"```(?:thinking|think)?\s*.*?```", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = cleaned.strip()
    if "Final Answer" in cleaned:
        cleaned = cleaned.split("Final Answer", 1)[-1].lstrip(":： \n")
    return cleaned.strip()


def safe_parse_json(text: str) -> Dict[str, str]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {}


def parse_role_action_text(text: str) -> Dict[str, str]:
    cleaned = strip_think_artifacts(text)
    if not cleaned:
        return {"speech": "", "action": ""}

    obj = safe_parse_json(cleaned)
    if obj:
        speech = str(obj.get("speech") or obj.get("发言") or obj.get("台词") or "").strip()
        action = str(obj.get("action") or obj.get("行动") or "").strip()
        if speech or action:
            return {"speech": speech, "action": action}

    speech_match = re.search(
        r"(?:^|\n)\s*(?:speech|发言|说的话)\s*[:：]\s*(.+?)(?=\n\s*(?:action|行动)\s*[:：]|\Z)",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    action_match = re.search(
        r"(?:^|\n)\s*(?:action|行动)\s*[:：]\s*(.+?)(?=\Z)",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if speech_match or action_match:
        return {
            "speech": speech_match.group(1).strip() if speech_match else "",
            "action": action_match.group(1).strip() if action_match else "",
        }

    lines = [line.strip(" -\t") for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return {"speech": "", "action": ""}
    if len(lines) == 1:
        return {"speech": "", "action": lines[0]}
    return {"speech": lines[0], "action": "\n".join(lines[1:]).strip()}


def build_model_story_context(game: Dict[str, Any]) -> str:
    if game.get("compressed_summary"):
        return (
            "【已压缩剧情概要】\n"
            + game.get("compressed_summary", "")
            + "\n\n【最近发生的正文】\n"
            + game.get("recent_story_for_context", "")
        )
    return game.get("main_story", "")


def estimate_text_tokens(text: str) -> int:
    return utils.estimate_tokens(strip_think_artifacts(text or ""))


def build_turn_action_context(actions: List[Dict[str, Any]]) -> str:
    if not actions:
        return ""
    blocks = []
    for action in actions:
        chunk = [f"角色：{action.get('role_name', '')}"]
        if action.get("speech"):
            chunk.append(f"发言：{action['speech']}")
        if action.get("action"):
            chunk.append(f"行动：{action['action']}")
        blocks.append("\n".join(chunk))
    return "\n\n".join(blocks)


def resolve_model_config(model_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    configs = utils.get_configs()
    models = configs.get("openai_models", [])
    requested = (model_info or {}).get("name")
    model_cfg = next((m for m in models if m.get("name") == requested), None)
    if not model_cfg and models:
        model_cfg = models[0]
    if not model_cfg:
        raise RuntimeError("No OpenAI-compatible model configured")
    sampling = configs.get("sampling_params", {"temperature": 0.7, "top_p": 0.9, "top_k": 40})
    return {
        "url": (model_cfg.get("url") or "").rstrip("/"),
        "model_name": model_cfg.get("model_name") or model_cfg.get("name"),
        "api_key": model_cfg.get("api_key") or "EMPTY",
        "sampling": sampling,
    }


def is_mistral_model(model_name: Optional[str]) -> bool:
    return "mistral" in str(model_name or "").lower()


def build_stream_request_options(
    model_name: Optional[str],
    enable_thinking: bool,
    sampling: Dict[str, Any],
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    if is_mistral_model(model_name):
        return {
            "temperature": 0.7 if enable_thinking else 0.1,
            "top_p": 0.95 if enable_thinking else None,
            "extra_body": {
                "reasoning_effort": "high" if enable_thinking else "none",
            },
        }
    return {
        "temperature": temperature if temperature is not None else sampling.get("temperature", 0.7),
        "top_p": sampling.get("top_p", 0.9),
        "extra_body": {
            "chat_template_kwargs": {"enable_thinking": bool(enable_thinking)},
        },
    }


def stream_chat_completion(
    messages: List[Dict[str, str]],
    model_info: Optional[Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    enable_thinking: bool = False,
) -> Iterable[str]:
    cfg = resolve_model_config(model_info)
    request_options = build_stream_request_options(
        cfg["model_name"],
        enable_thinking,
        cfg["sampling"],
        temperature,
    )
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
        "Connection": "close",
    }
    payload = {
        "model": cfg["model_name"],
        "messages": messages,
        "temperature": request_options["temperature"],
        "top_p": request_options["top_p"],
        "stream": True,
    }
    payload.update(request_options["extra_body"])
    with requests.post(
        f"{cfg['url']}/chat/completions",
        headers=headers,
        json=payload,
        stream=True,
        timeout=(10, 300),
    ) as resp:
        resp.encoding = "utf-8"
        if not resp.ok:
            error_text = resp.text[:1000]
            raise RuntimeError(f"模型服务返回 {resp.status_code}: {error_text}")
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choice = (chunk.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            content = delta.get("content") or delta.get("reasoning_content") or ""
            if content:
                yield content


def role_action_messages(game: Dict[str, Any], role: Dict[str, Any]) -> List[Dict[str, str]]:
    story_context = build_model_story_context(game)
    system_prompt = (
        "你正在扮演一个剧本杀场景中的角色。"
        "请直接给出这个角色本回合的发言内容和行动，不要输出推理过程。"
    )
    user_prompt = f"""
【当前场景】
{game.get("scene", "")}

【故事背景】
{game.get("background", "")}

【你的角色名】
{role.get("name", "")}

【你的角色公开信息】
{role.get("public_info", "")}

【你的角色目标 / 隐藏提示词】
{role.get("goal_prompt", "")}

【主故事线】
{story_context}

请直接输出两段：
发言：...
行动：...
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def role_action_messages_with_turn_context(
    game: Dict[str, Any],
    role: Dict[str, Any],
    prior_actions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    story_context = build_roleplay_context(game)
    turn_context = build_turn_action_context(prior_actions or [])
    system_prompt = (
        "你正在扮演一个剧本杀场景中的角色。"
        "请直接给出这个角色本回合的发言内容和行动，不要输出推理过程。"
    )
    user_prompt = f"""
【当前场景】
{game.get("scene", "")}

【故事背景】
{game.get("background", "")}

【你的角色名】
{role.get("name", "")}

【你的角色公开信息】
{role.get("public_info", "")}

【你的角色目标 / 隐藏提示词】
{role.get("goal_prompt", "")}

【最近状态上下文】
{story_context}

【本回合已发生的行动】
{turn_context or "本回合你是第一个行动的角色。"}

请直接输出两段：
发言：...
行动：...
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def resolution_messages(game: Dict[str, Any], turn: Dict[str, Any], actions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    story_context = build_model_story_context(game)
    on_hold_text = []
    for action in actions:
        chunk = f"角色：{action['role_name']}\n"
        if action.get("speech"):
            chunk += f"发言：{action['speech']}\n"
        if action.get("action"):
            chunk += f"行动：{action['action']}\n"
        on_hold_text.append(chunk.strip())

    system_prompt = (
        "你是剧本杀/跑团的主持 AI，负责根据所有角色本回合的 on hold 行动，"
        "综合判断本回合实际发生了什么。输出即将追加到主故事线的正文，"
        "不要输出 JSON，不要输出分析过程，不要替真人玩家做下一回合决定。"
    )
    user_prompt = f"""
【当前回合】
第 {turn["turn_no"]} 回合

【当前场景】
{game.get("scene", "")}

【故事背景】
{game.get("background", "")}

【主故事线】
{story_context}

【本回合 on hold 行动】
{chr(10).join(on_hold_text) if on_hold_text else "本回合没有角色行动。"}

请输出本回合最终发生的内容，用文学化正文书写。
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def resolution_messages(
    game: Dict[str, Any],
    turn: Dict[str, Any],
    actions: List[Dict[str, Any]],
    roles: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    role_map: Dict[str, Dict[str, Any]] = {}
    for role in roles or []:
        role_map[str(role.get("name") or "")] = role

    on_hold_text = []
    role_profiles = []
    for action in actions:
        role_name = str(action.get("role_name") or "")
        role = role_map.get(role_name, {})
        chunk = [f"角色：{role_name}"]
        if role.get("public_info"):
            chunk.append(f"人设公开信息：{role.get('public_info')}")
        if role.get("goal_prompt"):
            chunk.append(f"角色提示词：{role.get('goal_prompt')}")
        if action.get("speech"):
            chunk.append(f"发言：{action['speech']}")
        if action.get("action"):
            chunk.append(f"行动：{action['action']}")
        on_hold_text.append("\n".join(chunk))

        profile = [f"角色：{role_name}"]
        if role.get("public_info"):
            profile.append(f"人设公开信息：{role.get('public_info')}")
        if role.get("goal_prompt"):
            profile.append(f"角色提示词：{role.get('goal_prompt')}")
        role_profiles.append("\n".join(profile))

    system_prompt = (
        "你是剧本杀/跑团中的主持人与裁判 AI。"
        "你要基于场景、人设与双方行动内容，裁定这一回合实际发生了什么。"
        "先判断可行性再给结论：动作是否成功、失败或部分成功。"
        "不要因为角色自称成功就判定成功。"
        "角色原话尽量保留，不要输出分析过程，不要输出 JSON。"
    )
    user_prompt = f"""
【当前回合】
第 {turn["turn_no"]} 回合

【最近状态上下文】
{build_roleplay_context(game)}

【角色人设】
{chr(10).join(role_profiles) if role_profiles else "无"}

【双方行动内容】
{chr(10).join(on_hold_text) if on_hold_text else "本回合没有角色行动。"}

请输出管理员裁定内容。只输出本回合裁定结果，不写分析过程。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def narrative_messages(
    game: Dict[str, Any],
    turn: Dict[str, Any],
    roles: List[Dict[str, Any]],
    adjudication: str,
) -> List[Dict[str, str]]:
    story_context = build_model_story_context(game)
    role_blocks = []
    for role in roles:
        block = [f"角色名：{role.get('name', '')}"]
        if role.get("public_info"):
            block.append(f"公开信息：{role.get('public_info', '')}")
        if role.get("goal_prompt"):
            block.append(f"角色提示词：{role.get('goal_prompt', '')}")
        role_blocks.append("\n".join(block))

    system_prompt = (
        "你是剧本杀场景推演中的剧情执笔 AI。"
        "你已经拿到了经过人工审核的裁定结果，现在你的任务是把裁定结果写成可直接加入主故事线的正文。"
        "你必须严格服从裁定结果，不能推翻、篡改、弱化或强化裁定结论。"
        "你可以使用一定文学性和叙事性，让文本自然、连贯、可读，但不要写成散文化空抒情。"
        "角色说出口的话要尽量保留原意，可以自然嵌入叙事。"
        "只写这一回合最终实际发生的内容，不要写分析，不要写下一回合，不要输出 JSON。"
    )
    user_prompt = f"""
【当前回合】
第 {turn["turn_no"]} 回合

【当前场景】
{game.get("scene", "")}

【故事背景】
{game.get("background", "")}

【模型实际输入 / 既有上下文】
{story_context}

【角色信息与提示词】
{chr(10).join(role_blocks) if role_blocks else "无"}

【已经审核通过的裁定内容】
{adjudication}

请基于以上信息，把本回合结果写成一段可直接并入主故事线的正文。要求忠于裁定，语言自然，有一定文学性，但不要脱离事实。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


# Override the earlier prompt builders with clearer, stricter prompts.
def role_action_messages_with_turn_context(
    game: Dict[str, Any],
    role: Dict[str, Any],
    prior_actions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    story_context = build_roleplay_context(game)
    turn_context = build_turn_action_context(prior_actions or [])
    system_prompt = (
        "你正在扮演剧本杀场景中的一个角色。"
        "你只需要给出本回合最直接的发言和最直接的行动意图。"
        "不要写场景描写，不要写心理描写，不要写修辞，不要写铺垫，不要解释原因，不要输出推理过程。"
        "发言必须是角色真正要说出口的话，尽量短，1到2句即可。"
        "行动必须是角色本回合试图做的动作或目标，只说明要做什么，不要描述结果。"
        "不要把动作写成小说段落。"
    )
    user_prompt = f"""
【当前场景】
{game.get("scene", "")}

【故事背景】
{game.get("background", "")}

【你的角色名】
{role.get("name", "")}

【你的角色公开信息】
{role.get("public_info", "")}

【你的角色目标 / 隐藏提示词】
{role.get("goal_prompt", "")}

【最近状态上下文】
{story_context}

【本回合已发生的行动】
{turn_context or "本回合你是第一个行动的角色。"}

请严格按下面格式输出，保持简短：
发言：<角色要说的话，没有则写“无”>
行动：<角色试图做的动作，没有则写“无”>
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def resolution_messages(game: Dict[str, Any], turn: Dict[str, Any], actions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    story_context = build_model_story_context(game)
    on_hold_text = []
    for action in actions:
        chunk = f"角色：{action['role_name']}\n"
        if action.get("speech"):
            chunk += f"发言：{action['speech']}\n"
        if action.get("action"):
            chunk += f"行动：{action['action']}\n"
        on_hold_text.append(chunk.strip())

    system_prompt = (
        "你是剧本杀/跑团中的主持人与裁判 AI，负责根据所有角色本回合的 on hold 行动，判断这一回合实际发生了什么。"
        "你的职责不是复述角色意图，而是裁定结果。"
        "你必须先结合各角色的信息，再结合环境和位置，判断角色试图做的事情是否可行。"
        "角色说出口的话原则上原样保留，不做润色，不做裁判性改写，除非这句话在结果中根本无法成立。"
        "角色动作不能因为角色自己声称成功就算成功，必须经过裁定。"
        "双方冲突时，要考虑体型、力量、人数、准备程度、距离、道具、状态和环境。"
        "如果强势方对弱势方发起现实中明显占优的近身控制、攻击、压制或夺取，弱势方不能仅靠一句“挡住了”“挣脱了”就完全抵消，通常只能部分缓解或直接失败。"
        "你要输出最终客观结果，写清哪些动作成功，哪些失败，哪些部分成功。"
        "不要输出分析过程，不要输出 JSON，不要替玩家做下一回合决定。"
    )
    user_prompt = f"""
【当前回合】
第 {turn["turn_no"]} 回合

【当前场景】
{game.get("scene", "")}

【故事背景】
{game.get("background", "")}

【主故事线】
{story_context}

【本回合 on hold 行动】
{chr(10).join(on_hold_text) if on_hold_text else "本回合没有角色行动。"}

请输出本回合最终实际发生的内容。保留角色原话，重点裁定动作结果，写清成功、失败、未完成或部分成功。不要写分析过程。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def summary_messages(game: Dict[str, Any]) -> List[Dict[str, str]]:
    system_prompt = (
        "你是长篇互动剧本的剧情整理员。请把主故事线压缩成供后续模型继续游戏使用的概要。"
        "保留事实、人物关系、已发现线索、未解决疑点、每个角色当前状态，不要加入新剧情。"
    )
    user_prompt = f"""
【故事背景】
{game.get("background", "")}

【当前场景】
{game.get("scene", "")}

【完整主故事线】
{game.get("main_story", "")}

请生成压缩概要。
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]


def save_ai_action(project: str, game_id: int, turn_no: int, role: Dict[str, Any], raw: str) -> Dict[str, str]:
    parsed = parse_role_action_text(raw)
    speech = parsed["speech"]
    action = parsed["action"]
    if not speech and not action:
        action = raw.strip()
    ts = now_iso()
    with db_connection(project) as db:
        db.execute(
            """
            INSERT OR REPLACE INTO actions
            (game_id, turn_no, role_id, role_name, speech, action, source,
             raw_output, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'ai', ?, ?, ?)
            """,
            (game_id, turn_no, role["id"], role["name"], speech, action, raw, ts, ts),
        )
        db.commit()
    return {"role": role["name"], "speech": speech, "action": action}


def save_resolution(project: str, game_id: int, turn_no: int, resolution: str) -> None:
    resolution = strip_think_artifacts(resolution or "").strip()
    with db_connection(project) as db:
        db.execute(
            """
            UPDATE turns
            SET status = 'pending_review',
                pending_resolution = ?,
                updated_at = ?
            WHERE game_id = ? AND turn_no = ?
            """,
            (resolution, now_iso(), game_id, turn_no),
        )
        db.commit()


def save_narrative_draft(project: str, game_id: int, turn_no: int, narrative: str) -> None:
    narrative = strip_think_artifacts(narrative or "").strip()
    with db_connection(project) as db:
        db.execute(
            """
            UPDATE turns
            SET final_resolution = ?,
                updated_at = ?
            WHERE game_id = ? AND turn_no = ?
            """,
            (narrative, now_iso(), game_id, turn_no),
        )
        db.commit()


def save_summary(project: str, game_id: int, summary: str) -> None:
    game = fetch_game(project, game_id)
    if not game:
        return
    recent = (game["main_story"] or "")[-6000:]
    with db_connection(project) as db:
        db.execute(
            """
            UPDATE games
            SET compressed_summary = ?,
                recent_story_for_context = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (summary, recent, now_iso(), game_id),
        )
        db.commit()


def resolution_messages(
    game: Dict[str, Any],
    turn: Dict[str, Any],
    actions: List[Dict[str, Any]],
    roles: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    role_map: Dict[str, Dict[str, Any]] = {}
    for role in roles or []:
        role_map[str(role.get("name") or "")] = role

    role_profiles = []
    action_blocks = []
    for action in actions:
        role_name = str(action.get("role_name") or "")
        role = role_map.get(role_name, {})

        profile_lines = [f"角色：{role_name}"]
        if role.get("public_info"):
            profile_lines.append(f"人设公开信息：{role.get('public_info')}")
        if role.get("goal_prompt"):
            profile_lines.append(f"角色提示词：{role.get('goal_prompt')}")
        role_profiles.append("\n".join(profile_lines))

        action_lines = [f"角色：{role_name}"]
        if action.get("speech"):
            action_lines.append(f"发言：{action['speech']}")
        if action.get("action"):
            action_lines.append(f"行动：{action['action']}")
        action_blocks.append("\n".join(action_lines))

    system_prompt = (
        "你是剧本杀/跑团中的主持人与裁判 AI。"
        "你的任务是结算当前回合的实际结果，并给出每个角色在回合结束时的状态。"
        "你必须先判断行动是否可行，再裁定成功、失败或部分成功。"
        "不要因为角色自称成功就判定成功。"
        "不要写场景描写、氛围描写、文学化叙述、分析过程或 JSON。"
        "语言必须直白、简洁、客观，只描述当前状态与结果。"
        "你必须写出每个相关角色的状态，至少包括：情绪、体力、生命力，以及必要时的伤势、行动能力、受控状态、持有物变化。"
        "如果某项没有明显变化，也要明确写出当前状态。"
    )
    user_prompt = f"""
【当前回合】
第 {turn["turn_no"]} 回合

【最近状态上下文】
{build_roleplay_context(game) or "暂无既往管理员结算，当前请基于初始设定与本回合行动裁定。"}

【角色人设】
{chr(10).join(role_profiles) if role_profiles else "无"}

【双方行动内容】
{chr(10).join(action_blocks) if action_blocks else "本回合没有角色行动。"}

请按下面格式输出管理员结算，保持简洁直白：

【回合结果】
用 2-5 句写清这一回合最终实际发生了什么，只写结果，不写场景描述。

【角色状态】
对每个相关角色分别输出一段，格式如下：
角色名：
- 情绪：
- 体力：
- 生命力：
- 伤势：
- 行动能力：
- 当前状态：

如果有发言成立，可以在【回合结果】里保留关键原话；如果不成立，就不要强行保留。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.strip()},
    ]
