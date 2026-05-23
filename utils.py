import os
import sqlite3
import csv
import uuid
import shutil
import zipfile
import json
import re
from datetime import datetime

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.heic', '.heif'}

# ========================
# Path and Project Management
# ========================

def get_all_folders(path: str) -> list:
    """获取路径下所有文件夹名"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    items = os.listdir(path)
    folders = [item for item in items if os.path.isdir(os.path.join(path, item))]
    return folders

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = ['character', 'template', 'segment']
    for table in tables:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table} (
                name TEXT PRIMARY KEY,
                base_info TEXT,
                img_paths TEXT,
                extra_texts TEXT
            )
        ''')
    conn.commit()
    conn.close()

def upgrade_db(db_path):
    if not os.path.exists(db_path): return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = ['character', 'template', 'segment']
    for table in tables:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN extra_texts TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
    conn.commit()
    conn.close()

def ensure_project_structure(root_path, project_name):
    """确保项目资源目录存在，如果不存在则创建并初始化 SQLite 数据库"""
    pj_path = os.path.join(root_path, project_name)
    resource_path = os.path.join(pj_path, 'resource')
    os.makedirs(os.path.join(resource_path, 'pic'), exist_ok=True)
    os.makedirs(os.path.join(resource_path, 'gen_pic'), exist_ok=True)
    os.makedirs(os.path.join(resource_path, 'vd'), exist_ok=True)
    os.makedirs(os.path.join(resource_path, 'base'), exist_ok=True)
    os.makedirs(os.path.join(resource_path, 'base', 'cache', 'pic'), exist_ok=True)
    
    db_path = os.path.join(resource_path, 'database.db')
    
    # Auto-migration if CSV exists but DB doesn't
    if not os.path.exists(db_path) and os.path.exists(os.path.join(resource_path, 'chara_data.csv')):
        migrate_project_to_sqlite(pj_path)
    else:
        init_db(db_path)
        upgrade_db(db_path)
        
    return pj_path

def generate_unique_time_string_with_uuid():
    time_string = datetime.now().strftime('%Y%m%d%H%M%S%f')
    unique_id = uuid.uuid4().hex
    return f"{time_string}_{unique_id}"

# ========================
# Migration
# ========================

def migrate_project_to_sqlite(project_path):
    """将旧版使用 CSV 的项目转换为使用 SQLite 的新版项目"""
    resource_path = os.path.join(project_path, 'resource')
    db_path = os.path.join(resource_path, 'database.db')
    init_db(db_path)
    
    csv_mappings = {
        'chara_data.csv': 'character',
        'template_data.csv': 'template',
        'result_data.csv': 'segment'
    }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for csv_file, table_name in csv_mappings.items():
        csv_path = os.path.join(resource_path, csv_file)
        if os.path.exists(csv_path):
            with open(csv_path, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        name = row.get('name', '').strip()
                        if not name:
                            continue
                        cursor.execute(f"INSERT OR IGNORE INTO {table_name} (name, base_info, img_paths) VALUES (?, ?, ?)", 
                                     (name, row.get('base_info', ''), row.get('img_path', '')))
                    except Exception as e:
                        print(f"Error migrating {row.get('name')} in {csv_file}: {e}")
            
            # Optional: Rename or remove the old csv file after migration
            # os.rename(csv_path, csv_path + ".bak")
            
    conn.commit()
    conn.close()

# ========================
# DB Operations
# ========================

def read_db(db_path, table_name):
    """读取表中所有数据为字典列表"""
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows

def add_db_row(db_path, table_name, name, base_info, img_paths="", extra_texts="[]"):
    """添加一行数据"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(f"INSERT INTO {table_name} (name, base_info, img_paths, extra_texts) VALUES (?, ?, ?, ?)", (name, base_info, img_paths, extra_texts))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def update_db_row(db_path, table_name, name, new_name=None, base_info=None, img_paths=None, extra_texts=None):
    """更新某行数据"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    updates = []
    params = []
    if new_name is not None:
        updates.append("name = ?")
        params.append(new_name)
    if base_info is not None:
        updates.append("base_info = ?")
        params.append(base_info)
    if img_paths is not None:
        updates.append("img_paths = ?")
        params.append(img_paths)
    if extra_texts is not None:
        updates.append("extra_texts = ?")
        params.append(extra_texts)
        
    if not updates:
        conn.close()
        return False
        
    params.append(name)
    query = f"UPDATE {table_name} SET {', '.join(updates)} WHERE name = ?"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        success = cursor.rowcount > 0
    except Exception:
        success = False
    conn.close()
    return success

def remove_db_row(db_path, table_name, name):
    """删除某行数据"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE name = ?", (name,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

# ========================
# File System Operations
# ========================

def zip_directory(directory, zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, directory))

def unzip_directory(zip_file_path, extract_to_path):
    if not os.path.exists(extract_to_path):
        os.makedirs(extract_to_path)
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to_path)

def backup_project(projects_dir, project_name):
    """备份资源数据"""
    pj_path = os.path.join(projects_dir, project_name)
    resource_path = os.path.join(pj_path, 'resource')
    backup_folder = os.path.join(resource_path, 'back_up', generate_unique_time_string_with_uuid())
    os.makedirs(backup_folder, exist_ok=True)
    
    db_path = os.path.join(resource_path, 'database.db')
    if os.path.exists(db_path):
        shutil.copy2(db_path, os.path.join(backup_folder, 'database.db'))
    return backup_folder

# ========================
# Dialogs Management
# ========================

def get_dialogs_path(root_path, project_name):
    pj_path = ensure_project_structure(root_path, project_name)
    return os.path.join(pj_path, 'resource', 'base', 'dialog.json')

def get_dialogs(root_path, project_name):
    path = get_dialogs_path(root_path, project_name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_dialog(root_path, project_name, dialog_id, title, messages):
    path = get_dialogs_path(root_path, project_name)
    dialogs = get_dialogs(root_path, project_name)
    
    found = False
    for d in dialogs:
        if d.get('id') == dialog_id:
            d['title'] = title
            d['messages'] = messages
            found = True
            break
            
    if not found:
        dialogs.insert(0, {
            'id': dialog_id,
            'title': title,
            'messages': messages
        })
        
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(dialogs, f, ensure_ascii=False, indent=2)

def delete_dialog(root_path, project_name, dialog_id):
    path = get_dialogs_path(root_path, project_name)
    dialogs = get_dialogs(root_path, project_name)
    
    new_dialogs = [d for d in dialogs if d.get('id') != dialog_id]
    
    if len(new_dialogs) < len(dialogs):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(new_dialogs, f, ensure_ascii=False, indent=2)
        return True
    return False

# ========================
# Config Management
# ========================

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configs.json')

IMAGE_SERVICE_PARAM_TYPES = {
    "negative_prompt": "text",
    "height": "int",
    "width": "int",
    "num_inference_steps": "int",
    "guidance_scale": "float",
    "cfg_normalization": "boolean",
    "seed": "int",
    "output_dir": "text",
    "output_name": "text"
}

DEFAULT_IMAGE_SERVICE_CONFIGS = [
    {
        "name": "Z-Image 6000",
        "service_type": "zimage",
        "url": "http://localhost:6000",
        "default_params": {
            "negative_prompt": "",
            "height": 1024,
            "width": 1024,
            "num_inference_steps": 8,
            "guidance_scale": 0.0,
            "cfg_normalization": False,
            "seed": 42,
            "output_dir": "outputs",
            "output_name": ""
        },
        "enabled_params": [
            "height",
            "width",
            "num_inference_steps",
            "guidance_scale",
            "seed",
            "output_dir",
            "output_name"
        ],
        "param_types": dict(IMAGE_SERVICE_PARAM_TYPES)
    },
    {
        "name": "Z-Image 6001",
        "service_type": "zimage",
        "url": "http://localhost:6001",
        "default_params": {
            "negative_prompt": "",
            "height": 1280,
            "width": 720,
            "num_inference_steps": 50,
            "guidance_scale": 4.0,
            "cfg_normalization": False,
            "seed": 42,
            "output_dir": "outputs",
            "output_name": ""
        },
        "enabled_params": [
            "negative_prompt",
            "height",
            "width",
            "num_inference_steps",
            "guidance_scale",
            "cfg_normalization",
            "seed",
            "output_dir",
            "output_name"
        ],
        "param_types": dict(IMAGE_SERVICE_PARAM_TYPES)
    }
]

IMAGE_SERVICE_TYPE_DEFAULTS = {
    "zimage": {
        "default_params": {
            "negative_prompt": "",
            "height": 1024,
            "width": 1024,
            "num_inference_steps": 8,
            "guidance_scale": 0.0,
            "cfg_normalization": False,
            "seed": 42,
            "output_dir": "outputs",
            "output_name": ""
        },
        "enabled_params": [
            "negative_prompt",
            "height",
            "width",
            "num_inference_steps",
            "guidance_scale",
            "cfg_normalization",
            "seed",
            "output_dir",
            "output_name"
        ],
        "param_types": dict(IMAGE_SERVICE_PARAM_TYPES)
    },
    "hidream_o1": {
        "default_params": {
            "mode": "t2i",
            "width": 2048,
            "height": 2048,
            "seed": 32,
            "num_inference_steps": 50,
            "guidance_scale": 5.0,
            "shift": 3.0,
            "scheduler_name": "default",
            "editing_scheduler": "flow_match",
            "keep_original_aspect": True,
            "preview_steps": "7,14,21"
        },
        "enabled_params": [
            "mode",
            "width",
            "height",
            "seed",
            "num_inference_steps",
            "guidance_scale",
            "shift",
            "scheduler_name",
            "editing_scheduler",
            "keep_original_aspect",
            "preview_steps"
        ],
        "param_types": {
            "mode": "text",
            "width": "int",
            "height": "int",
            "seed": "int",
            "num_inference_steps": "int",
            "guidance_scale": "float",
            "shift": "float",
            "scheduler_name": "text",
            "editing_scheduler": "text",
            "keep_original_aspect": "boolean",
            "preview_steps": "text"
        }
    }
}


def infer_image_param_type(value):
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, int) and not isinstance(value, bool):
        return 'int'
    if isinstance(value, float):
        return 'float'
    return 'text'


def _merge_param_types(default_params, param_types=None):
    merged = {}
    for key, value in (default_params or {}).items():
        merged[key] = infer_image_param_type(value)
    for key, value in IMAGE_SERVICE_PARAM_TYPES.items():
        merged.setdefault(key, value)
    for key, value in (param_types or {}).items():
        merged[key] = value or merged.get(key, 'text')
    return merged


def get_default_image_service_configs():
    return [normalize_image_service_config(item) for item in DEFAULT_IMAGE_SERVICE_CONFIGS]


def normalize_image_service_config(service):
    raw = dict(service or {})
    name = str(raw.get('name') or '').strip()
    url = str(raw.get('url') or '').strip()
    service_type = str(raw.get('service_type') or 'zimage').strip() or 'zimage'
    default_match = next((item for item in DEFAULT_IMAGE_SERVICE_CONFIGS if item['name'] == name), None)
    type_defaults = IMAGE_SERVICE_TYPE_DEFAULTS.get(service_type, IMAGE_SERVICE_TYPE_DEFAULTS['zimage'])

    normalized = {
        'name': name or (default_match or {}).get('name', 'Image Service'),
        'url': url or (default_match or {}).get('url', ''),
        'service_type': service_type
    }

    default_params = dict(type_defaults.get('default_params', {}))
    if default_match:
        default_params.update(default_match.get('default_params', {}))
    default_params.update(raw.get('default_params') or {})
    normalized['default_params'] = default_params

    enabled_params = raw.get('enabled_params')
    if enabled_params is None and default_match:
        enabled_params = list(default_match.get('enabled_params', []))
    if enabled_params is None:
        enabled_params = list(type_defaults.get('enabled_params', default_params.keys()))
    normalized['enabled_params'] = list(dict.fromkeys(
        str(key).strip() for key in enabled_params if str(key).strip()
    ))

    normalized['param_types'] = _merge_param_types(
        default_params,
        raw.get('param_types') or (default_match or {}).get('param_types') or type_defaults.get('param_types')
    )
    return normalized


def normalize_image_service_configs(configs):
    merged = []
    for item in configs or []:
        service = normalize_image_service_config(item)
        if service.get('name'):
            merged.append(service)
    return merged

def get_configs():
    default_image_services = get_default_image_service_configs()
    if not os.path.exists(CONFIG_PATH):
        default_config = {
            "openai_models": [
                {
                    "name": "Qwen3.6-27B",
                    "url": "http://10.10.11.22:5000/v1",
                    "model_name": "Qwen3.6-27B"
                }
            ],
            "sampling_params": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40
            },
            "image_service": {
                "base_url": "http://localhost:6000"
            },
            "image_services": default_image_services,
            "selected_image_service": "Z-Image 6000"
        }
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        if 'sampling_params' not in configs:
            configs['sampling_params'] = {"temperature": 0.7, "top_p": 0.9, "top_k": 40}
        if 'image_service' not in configs:
            configs['image_service'] = {"base_url": "http://localhost:6000"}
        if 'image_services' not in configs:
            base_url = configs.get('image_service', {}).get('base_url', "http://localhost:6000")
            configs['image_services'] = [{
                "name": "Z-Image 6000",
                "url": base_url,
                "default_params": default_image_services[0]['default_params'],
                "enabled_params": default_image_services[0]['enabled_params'],
                "param_types": default_image_services[0]['param_types']
            }]
            if base_url.rstrip('/') != "http://localhost:6001":
                configs['image_services'].append(default_image_services[1])
        configs['image_services'] = normalize_image_service_configs(configs.get('image_services', []))
        if 'selected_image_service' not in configs:
            configs['selected_image_service'] = configs.get('image_services', default_image_services)[0].get('name', "Z-Image 6000")
        if not any(s.get('name') == configs['selected_image_service'] for s in configs.get('image_services', [])):
            configs['selected_image_service'] = configs.get('image_services', default_image_services)[0].get('name', "Z-Image 6000")
        selected_service = next(
            (s for s in configs.get('image_services', []) if s.get('name') == configs['selected_image_service']),
            configs.get('image_services', [{}])[0]
        )
        configs['image_service'] = {'base_url': (selected_service or {}).get('url', "http://localhost:6000")}
        try:
            save_configs(configs)
        except Exception:
            pass
        return configs
    except Exception:
        return {"openai_models": []}

def save_configs(configs):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)

# ========================
# Token Counting
# ========================

def estimate_tokens(text):
    if not text: return 0
    # CJK characters: count as 1 token each
    cjk_pattern = re.compile(r'[\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')
    cjk_count = len(cjk_pattern.findall(text))
    
    # Non-CJK text: count words / 0.75
    non_cjk_text = cjk_pattern.sub(' ', text)
    words = non_cjk_text.split()
    non_cjk_tokens = len(words) / 0.75
    
    return int(cjk_count + non_cjk_tokens)

def strip_think_tags(text):
    if not text: return ""
    return re.sub(r'<think>.*?(?:</think>|$)', '', text, flags=re.DOTALL)

def count_messages_tokens(messages):
    total = 0
    no_think_total = 0
    for m in messages:
        text = m.get('text', '')
        total += estimate_tokens(text)
        no_think_total += estimate_tokens(strip_think_tags(text))
    return {"count": total, "count_no_think": no_think_total}


def _normalize_path(path):
    if not path:
        return ''
    return os.path.normcase(os.path.abspath(path))


def _is_within(parent_path, child_path):
    parent_abs = _normalize_path(parent_path)
    child_abs = _normalize_path(child_path)
    return child_abs == parent_abs or child_abs.startswith(parent_abs + os.sep)


def _is_image_file(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def _relative_resource_path(resource_root, file_path):
    rel = os.path.relpath(file_path, resource_root).replace(os.sep, '/')
    return rel if rel != '.' else ''


def build_project_resource_url(project_name, resource_root, file_path):
    rel = _relative_resource_path(resource_root, file_path)
    return f"/static/projects/{project_name}/resource/{rel}" if rel else ''


def resolve_project_resource_path(resource_root, raw_path):
    if not raw_path:
        return None

    candidate = str(raw_path).strip().replace('/', os.sep)
    if not candidate:
        return None

    if os.path.isabs(candidate):
        abs_path = os.path.abspath(candidate)
    else:
        trimmed = candidate
        if trimmed.startswith(f"resource{os.sep}"):
            trimmed = trimmed[len("resource" + os.sep):]
        abs_path = os.path.abspath(os.path.join(resource_root, trimmed))

    if not _is_within(resource_root, abs_path):
        return None
    return abs_path


def _parse_character_image_refs(project_name, resource_root, img_paths):
    refs = []
    raw_value = (img_paths or '').strip()
    if not raw_value:
        return refs

    parsed_entries = None
    if raw_value.startswith('[') or raw_value.startswith('{'):
        try:
            parsed_entries = json.loads(raw_value)
        except Exception:
            parsed_entries = None

    if isinstance(parsed_entries, dict):
        parsed_entries = [parsed_entries]

    if isinstance(parsed_entries, list):
        for entry in parsed_entries:
            if isinstance(entry, dict):
                raw_path = entry.get('path') or entry.get('url')
            else:
                raw_path = entry
            abs_path = resolve_project_resource_path(resource_root, raw_path)
            if not abs_path or not _is_image_file(abs_path):
                continue
            refs.append({
                'path': abs_path,
                'url': build_project_resource_url(project_name, resource_root, abs_path)
            })
        return refs

    abs_path = resolve_project_resource_path(resource_root, raw_value)
    if abs_path and _is_image_file(abs_path):
        refs.append({
            'path': abs_path,
            'url': build_project_resource_url(project_name, resource_root, abs_path)
        })
    return refs


def get_chat_gallery(root_path, project_name):
    pj_path = ensure_project_structure(root_path, project_name)
    resource_root = os.path.join(pj_path, 'resource')
    cache_root = os.path.join(resource_root, 'base', 'cache', 'pic')
    dialogs = get_dialogs(root_path, project_name)
    items = {}

    for dialog in dialogs:
        dialog_id = dialog.get('id', '')
        dialog_title = dialog.get('title') or '未命名对话'
        messages = dialog.get('messages', [])
        for idx, message in enumerate(messages):
            media_type = message.get('media_type')
            media_path = resolve_project_resource_path(resource_root, message.get('media_path'))
            if not media_path and message.get('media_url'):
                media_path = resolve_project_resource_path(resource_root, message.get('media_url'))
            if not media_path or not _is_image_file(media_path):
                continue
            if media_type and media_type != 'image':
                continue

            normalized = _normalize_path(media_path)
            item = items.setdefault(normalized, {
                'id': normalized,
                'scope': 'chat',
                'path': media_path,
                'url': build_project_resource_url(project_name, resource_root, media_path),
                'filename': os.path.basename(media_path),
                'dialog_ids': set(),
                'dialog_titles': set(),
                'message_indexes': [],
                'updated_at': '',
                'size': 0
            })
            item['dialog_ids'].add(dialog_id)
            item['dialog_titles'].add(dialog_title)
            item['message_indexes'].append(idx)

    if os.path.exists(cache_root):
        for file_name in os.listdir(cache_root):
            abs_path = os.path.join(cache_root, file_name)
            if not os.path.isfile(abs_path) or not _is_image_file(abs_path):
                continue
            normalized = _normalize_path(abs_path)
            items.setdefault(normalized, {
                'id': normalized,
                'scope': 'chat',
                'path': abs_path,
                'url': build_project_resource_url(project_name, resource_root, abs_path),
                'filename': os.path.basename(abs_path),
                'dialog_ids': set(),
                'dialog_titles': set(),
                'message_indexes': [],
                'updated_at': '',
                'size': 0
            })

    results = []
    for item in items.values():
        if os.path.exists(item['path']):
            stat = os.stat(item['path'])
            item['updated_at'] = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds')
            item['size'] = stat.st_size
        results.append({
            'id': item['id'],
            'scope': item['scope'],
            'path': item['path'],
            'url': item['url'],
            'filename': item['filename'],
            'dialog_count': len(item['dialog_ids']),
            'dialog_titles': sorted(item['dialog_titles']),
            'message_count': len(item['message_indexes']),
            'updated_at': item['updated_at'],
            'size': item['size']
        })

    results.sort(key=lambda x: (x['updated_at'], x['filename']), reverse=True)
    return results


def get_character_gallery(root_path, project_name):
    pj_path = ensure_project_structure(root_path, project_name)
    resource_root = os.path.join(pj_path, 'resource')
    pic_root = os.path.join(resource_root, 'pic')
    characters = read_db(os.path.join(resource_root, 'database.db'), 'character')

    items = {}
    for character in characters:
        character_name = character.get('name') or '未命名角色'
        for ref in _parse_character_image_refs(project_name, resource_root, character.get('img_paths')):
            normalized = _normalize_path(ref['path'])
            item = items.setdefault(normalized, {
                'id': normalized,
                'scope': 'character',
                'path': ref['path'],
                'url': ref['url'],
                'filename': os.path.basename(ref['path']),
                'character_names': set(),
                'updated_at': '',
                'size': 0
            })
            item['character_names'].add(character_name)

    if os.path.exists(pic_root):
        for file_name in os.listdir(pic_root):
            abs_path = os.path.join(pic_root, file_name)
            if not os.path.isfile(abs_path) or not _is_image_file(abs_path):
                continue
            normalized = _normalize_path(abs_path)
            items.setdefault(normalized, {
                'id': normalized,
                'scope': 'character',
                'path': abs_path,
                'url': build_project_resource_url(project_name, resource_root, abs_path),
                'filename': os.path.basename(abs_path),
                'character_names': set(),
                'updated_at': '',
                'size': 0
            })

    results = []
    for item in items.values():
        if os.path.exists(item['path']):
            stat = os.stat(item['path'])
            item['updated_at'] = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds')
            item['size'] = stat.st_size
        results.append({
            'id': item['id'],
            'scope': item['scope'],
            'path': item['path'],
            'url': item['url'],
            'filename': item['filename'],
            'character_names': sorted(item['character_names']),
            'in_use': bool(item['character_names']),
            'updated_at': item['updated_at'],
            'size': item['size']
        })

    results.sort(key=lambda x: (x['in_use'], x['updated_at'], x['filename']), reverse=True)
    return results


def get_generated_gallery(root_path, project_name):
    pj_path = ensure_project_structure(root_path, project_name)
    resource_root = os.path.join(pj_path, 'resource')
    gen_root = os.path.join(resource_root, 'gen_pic')
    items = []

    if os.path.exists(gen_root):
        for file_name in os.listdir(gen_root):
            abs_path = os.path.join(gen_root, file_name)
            if not os.path.isfile(abs_path) or not _is_image_file(abs_path):
                continue
            stat = os.stat(abs_path)
            items.append({
                'id': _normalize_path(abs_path),
                'scope': 'generated',
                'path': abs_path,
                'url': build_project_resource_url(project_name, resource_root, abs_path),
                'filename': os.path.basename(abs_path),
                'updated_at': datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds'),
                'size': stat.st_size
            })

    items.sort(key=lambda x: (x['updated_at'], x['filename']), reverse=True)
    return items


def get_gallery_summary(root_path, project_name):
    return {
        'chat': get_chat_gallery(root_path, project_name),
        'character': get_character_gallery(root_path, project_name),
        'generated': get_generated_gallery(root_path, project_name)
    }


def delete_chat_gallery_image(root_path, project_name, image_path):
    pj_path = ensure_project_structure(root_path, project_name)
    resource_root = os.path.join(pj_path, 'resource')
    cache_root = os.path.join(resource_root, 'base', 'cache', 'pic')
    target_path = resolve_project_resource_path(resource_root, image_path)
    if not target_path or not _is_within(cache_root, target_path):
        return False, 'invalid_path'

    dialogs = get_dialogs(root_path, project_name)
    normalized_target = _normalize_path(target_path)
    changed = False

    for dialog in dialogs:
        for message in dialog.get('messages', []):
            msg_path = resolve_project_resource_path(resource_root, message.get('media_path'))
            if msg_path and _normalize_path(msg_path) == normalized_target:
                message.pop('media_path', None)
                message.pop('media_url', None)
                message.pop('media_type', None)
                changed = True

    if changed:
        with open(get_dialogs_path(root_path, project_name), 'w', encoding='utf-8') as f:
            json.dump(dialogs, f, ensure_ascii=False, indent=2)

    if os.path.exists(target_path):
        os.remove(target_path)
    return True, 'deleted'


def delete_character_gallery_image(root_path, project_name, image_path):
    pj_path = ensure_project_structure(root_path, project_name)
    resource_root = os.path.join(pj_path, 'resource')
    pic_root = os.path.join(resource_root, 'pic')
    target_path = resolve_project_resource_path(resource_root, image_path)
    if not target_path or not _is_within(pic_root, target_path):
        return False, 'invalid_path'

    gallery_items = get_character_gallery(root_path, project_name)
    target_item = next((item for item in gallery_items if _normalize_path(item['path']) == _normalize_path(target_path)), None)
    if target_item and target_item['in_use']:
        return False, 'in_use'

    if os.path.exists(target_path):
        os.remove(target_path)
    return True, 'deleted'


def delete_generated_gallery_image(root_path, project_name, image_path):
    pj_path = ensure_project_structure(root_path, project_name)
    resource_root = os.path.join(pj_path, 'resource')
    gen_root = os.path.join(resource_root, 'gen_pic')
    target_path = resolve_project_resource_path(resource_root, image_path)
    if not target_path or not _is_within(gen_root, target_path):
        return False, 'invalid_path'

    dialogs = get_dialogs(root_path, project_name)
    normalized_target = _normalize_path(target_path)
    changed = False
    for dialog in dialogs:
        for message in dialog.get('messages', []):
            msg_path = resolve_project_resource_path(resource_root, message.get('media_path'))
            if msg_path and _normalize_path(msg_path) == normalized_target:
                message.pop('media_path', None)
                message.pop('media_url', None)
                message.pop('media_type', None)
                changed = True

    if changed:
        with open(get_dialogs_path(root_path, project_name), 'w', encoding='utf-8') as f:
            json.dump(dialogs, f, ensure_ascii=False, indent=2)

    if os.path.exists(target_path):
        os.remove(target_path)
    return True, 'deleted'
