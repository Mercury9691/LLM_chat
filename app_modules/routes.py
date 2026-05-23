import json
import os

import requests
from flask import Response, jsonify, render_template, request, send_file, stream_with_context
from openai import OpenAI

from app_modules.config import IMAGE_SERVICE_BASE_URL, OLLAMA_BASE_URL, PROJECTS_DIR
from app_modules.helpers import get_current_project, get_db_path, save_uploaded_file
from app_modules.services import scenario_service
from app_modules.services.chat_service import (
    generate_ollama,
    generate_vllm,
    rewrite_prompt_ollama,
    rewrite_prompt_vllm,
)
from app_modules.services.image_service import (
    build_image_generation_payload,
    finalize_generated_result,
    get_image_service_by_name,
    get_image_service_type,
    get_image_service_url,
    get_remembered_image_job_payload,
    get_selected_image_service,
    image_service_get,
    image_service_post,
    is_hidream_service,
    remember_image_job_payload,
    test_image_service_url_by_type,
    test_image_service_url,
    test_openai_model_config,
)
import utils


# ========================
# Pages
# ========================

# @app.route('/')
def index():
    return render_template('index.html')

# @app.route('/gallery/<project>/<name>')
def gallery(project, name):
    return render_template('gallery.html', project=project, name=name)

# ========================
# Project APIs
# ========================

# @app.route('/api/projects', methods=['GET'])
def get_projects():
    folders = utils.get_all_folders(PROJECTS_DIR)
    if not folders:
        utils.ensure_project_structure(PROJECTS_DIR, 'default')
        folders = ['default']
    return jsonify({'projects': folders})

# @app.route('/api/project', methods=['POST'])
def create_project():
    name = request.json.get('name')
    if not name: return jsonify({'error': 'Name is required'}), 400
    utils.ensure_project_structure(PROJECTS_DIR, name)
    return jsonify({'success': True, 'project': name})

# ========================
# DB CRUD APIs
# ========================

# @app.route('/api/data/<data_type>', methods=['GET'])
def get_data(data_type):
    project = get_current_project(request)
    path = get_db_path(project)
    if data_type not in ['character', 'template', 'segment']: return jsonify({'error': 'Invalid type'}), 400
    data = utils.read_db(path, data_type)
    return jsonify(data)

# @app.route('/api/data/<data_type>', methods=['POST'])
def add_data(data_type):
    project = get_current_project(request)
    path = get_db_path(project)
    data = request.json
    success = utils.add_db_row(path, data_type, data.get('name'), data.get('base_info'), data.get('img_paths', '[]'), data.get('extra_texts', '[]'))
    return jsonify({'success': success})

# @app.route('/api/data/<data_type>/<name>', methods=['PUT'])
def update_data(data_type, name):
    project = get_current_project(request)
    path = get_db_path(project)
    data = request.json
    success = utils.update_db_row(path, data_type, name, new_name=data.get('new_name'), base_info=data.get('base_info'), img_paths=data.get('img_paths'), extra_texts=data.get('extra_texts'))
    return jsonify({'success': success})

# @app.route('/api/data/<data_type>/<name>', methods=['DELETE'])
def delete_data(data_type, name):
    project = get_current_project(request)
    path = get_db_path(project)
    success = utils.remove_db_row(path, data_type, name)
    return jsonify({'success': success})


# @app.route('/api/gallery', methods=['GET'])
def get_gallery():
    project = get_current_project(request)
    scope = request.args.get('scope')
    gallery = utils.get_gallery_summary(PROJECTS_DIR, project)
    if scope in ('chat', 'character', 'generated'):
        return jsonify({scope: gallery.get(scope, [])})
    return jsonify(gallery)


# @app.route('/api/gallery/<scope>', methods=['DELETE'])
def delete_gallery_item(scope):
    project = get_current_project(request)
    image_path = (request.json or {}).get('path')
    if not image_path:
        return jsonify({'error': 'Path is required'}), 400

    if scope == 'chat':
        success, reason = utils.delete_chat_gallery_image(PROJECTS_DIR, project, image_path)
    elif scope == 'character':
        success, reason = utils.delete_character_gallery_image(PROJECTS_DIR, project, image_path)
    elif scope == 'generated':
        success, reason = utils.delete_generated_gallery_image(PROJECTS_DIR, project, image_path)
    else:
        return jsonify({'error': 'Invalid gallery scope'}), 400

    status = 200 if success else 400
    return jsonify({'success': success, 'reason': reason}), status


# @app.route('/api/image-service/health', methods=['GET'])
def image_service_health():
    service = get_selected_image_service()
    base_url = get_image_service_url()
    return jsonify(test_image_service_url_by_type(base_url, get_image_service_type(service)))


# @app.route('/api/image-service/generate', methods=['POST'])
def image_service_generate():
    project = get_current_project(request)
    data = request.json or {}
    service = get_selected_image_service()
    payload = build_image_generation_payload(data, service)
    if not payload:
        return jsonify({'error': 'Prompt is required'}), 400

    base_url = (service.get('url') or IMAGE_SERVICE_BASE_URL).rstrip('/')
    try:
        if is_hidream_service(service):
            submit_resp = image_service_post(f"{base_url}/v1/generate", json=payload, timeout=30)
            submit_resp.raise_for_status()
            submit_result = submit_resp.json()
            job_id = submit_result.get('job_id')
            remember_image_job_payload(job_id, payload)
            if not job_id:
                return jsonify({'error': 'Image service did not return job_id', 'service_response': submit_result}), 502
            result_resp = image_service_get(f"{base_url}/v1/jobs/{job_id}/result", timeout=600)
            result_resp.raise_for_status()
            result = result_resp.json()
            final_result = finalize_generated_result(project, payload, result)
            if not final_result:
                return jsonify({'error': 'Image service did not return image', 'service_response': result}), 502
            return jsonify(final_result)
        resp = image_service_post(f"{base_url}/generate", json=payload, timeout=600)
        resp.raise_for_status()
        result = resp.json()
        final_result = finalize_generated_result(project, payload, result)
        if not final_result:
            return jsonify({'error': 'Image service did not return base64', 'service_response': result}), 502
        return jsonify(final_result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 502


# @app.route('/api/image-service/generate_async', methods=['POST'])
def image_service_generate_async():
    data = request.json or {}
    service = get_selected_image_service()
    payload = build_image_generation_payload(data, service)
    if not payload:
        return jsonify({'error': 'Prompt is required'}), 400

    base_url = (service.get('url') or IMAGE_SERVICE_BASE_URL).rstrip('/')
    try:
        endpoint = "/v1/generate" if is_hidream_service(service) else "/generate_async"
        resp = image_service_post(f"{base_url}{endpoint}", json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        remember_image_job_payload(result.get('job_id'), payload)
        return jsonify({
            'success': True,
            'job_id': result.get('job_id'),
            'status': result.get('status', 'queued'),
            'params': payload,
            'service': {
                'name': service.get('name'),
                'url': base_url,
                'service_type': get_image_service_type(service)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 502


# @app.route('/api/image-service/progress/<job_id>', methods=['GET'])
def image_service_progress(job_id):
    service = get_image_service_by_name(request.args.get('service'))
    base_url = (service.get('url') or IMAGE_SERVICE_BASE_URL).rstrip('/')
    progress_path = f"/v1/jobs/{job_id}/events" if is_hidream_service(service) else f"/progress/{job_id}"

    @stream_with_context
    def generate():
        try:
            with image_service_get(f"{base_url}{progress_path}", stream=True, timeout=(10, 610)) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if line is None:
                        continue
                    if line == '':
                        yield '\n'
                    else:
                        yield f"{line}\n"
        except Exception as e:
            error_payload = json.dumps({
                'type': 'error',
                'job_id': job_id,
                'message': str(e)
            }, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


# @app.route('/api/image-service/result/<job_id>', methods=['GET'])
def image_service_result(job_id):
    project = get_current_project(request)
    service = get_image_service_by_name(request.args.get('service'))
    base_url = (service.get('url') or IMAGE_SERVICE_BASE_URL).rstrip('/')
    try:
        result_path = f"/v1/jobs/{job_id}/result" if is_hidream_service(service) else f"/result/{job_id}"
        resp = image_service_get(f"{base_url}{result_path}", timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if not is_hidream_service(service) and result.get('status') != 'done':
            return jsonify({'success': False, 'service_response': result}), 409

        payload = get_remembered_image_job_payload(job_id) or build_image_generation_payload(request.args, service)
        if not payload:
            payload = {'prompt': request.args.get('prompt', '')}

        final_result = finalize_generated_result(project, payload, result)
        if not final_result:
            return jsonify({'error': 'Image service result did not include base64', 'service_response': result}), 502
        return jsonify(final_result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 502

# ========================
# Dialog APIs
# ========================

# @app.route('/api/dialogs', methods=['GET'])
def get_dialogs():
    project = get_current_project(request)
    dialogs = utils.get_dialogs(PROJECTS_DIR, project)
    # We might not want to return all messages for the list to save bandwidth, 
    # but since it's a local app, it's fine. Or we can strip messages:
    # return jsonify([{'id': d['id'], 'title': d['title']} for d in dialogs])
    return jsonify(dialogs)

# @app.route('/api/dialogs/<dialog_id>', methods=['POST'])
def save_dialog(dialog_id):
    project = get_current_project(request)
    data = request.json
    title = data.get('title', '新对话')
    messages = data.get('messages', [])
    utils.save_dialog(PROJECTS_DIR, project, dialog_id, title, messages)
    return jsonify({'success': True})

# @app.route('/api/dialogs/<dialog_id>', methods=['DELETE'])
def delete_dialog(dialog_id):
    project = get_current_project(request)
    success = utils.delete_dialog(PROJECTS_DIR, project, dialog_id)
    return jsonify({'success': success})

# ========================
# File System & System APIs
# ========================

# @app.route('/api/upload', methods=['POST'])
def upload_file():
    project = get_current_project(request)
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400

    file = request.files['file']
    target = request.form.get('target', 'crud')
    pj_path = utils.ensure_project_structure(PROJECTS_DIR, project)

    if target == 'chat':
        save_dir = os.path.join(pj_path, 'resource', 'base', 'cache', 'pic')
    else:
        save_dir = os.path.join(pj_path, 'resource', 'pic')

    file_path, _ = save_uploaded_file(file, save_dir, utils.generate_unique_time_string_with_uuid())
    media_url = f"/static/projects/{project}/resource/{os.path.relpath(file_path, os.path.join(pj_path, 'resource')).replace(os.sep, '/')}"
    return jsonify({'url': media_url, 'path': file_path})

# Serve project static files
# @app.route('/static/projects/<project>/resource/<path:resource_path>')
def serve_project_file(project, resource_path):
    resource_root = os.path.join(PROJECTS_DIR, project, 'resource')
    path = os.path.abspath(os.path.join(resource_root, resource_path))
    root_abs = os.path.abspath(resource_root)
    if not (path == root_abs or path.startswith(root_abs + os.sep)):
        return "Invalid path", 400
    if os.path.exists(path):
        return send_file(path)
    return "File not found", 404

# @app.route('/api/system/backup', methods=['POST'])
def backup_system():
    project = get_current_project(request)
    backup_folder = utils.backup_project(PROJECTS_DIR, project)
    return jsonify({'success': True, 'path': backup_folder})

# @app.route('/api/system/export', methods=['GET'])
def export_system():
    project = request.args.get('project')
    if not project: return jsonify({'error': 'Project parameter required'}), 400
    
    pj_path = os.path.join(PROJECTS_DIR, project)
    zip_path = os.path.join(PROJECTS_DIR, f"{project}_export.zip")
    utils.zip_directory(pj_path, zip_path)
    
    return send_file(zip_path, as_attachment=True)

# ========================
# Chat APIs (Legacy updated)
# ========================

# @app.route('/models', methods=['GET'])
def get_models():
    configs = utils.get_configs()
    models = []
    for m in configs.get('openai_models', []):
        models.append({"name": m['name'], "source": "OpenAI", "multimodal": True})
        
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1)
        if resp.status_code == 200:
            for m in resp.json().get('models', []):
                name = m['name']
                is_mm = any(kw in name.lower() for kw in ['llava', 'vl', 'vision', 'minicpm'])
                models.append({"name": name, "source": "Ollama", "multimodal": is_mm})
    except Exception: pass
    return jsonify(models)

# @app.route('/api/config/models', methods=['GET', 'POST'])
def manage_openai_models():
    configs = utils.get_configs()
    if request.method == 'POST':
        new_models = request.json # Expecting the full list of models
        configs['openai_models'] = new_models
        utils.save_configs(configs)
        return jsonify({"success": True})
    return jsonify(configs.get('openai_models', []))


# @app.route('/api/config/image-services', methods=['GET', 'POST'])
def manage_image_services():
    configs = utils.get_configs()
    if request.method == 'POST':
        data = request.json or {}
        services = utils.normalize_image_service_configs(data.get('services', []))
        selected = data.get('selected')
        configs['image_services'] = services
        if selected and any(s.get('name') == selected for s in services):
            configs['selected_image_service'] = selected
        elif services:
            configs['selected_image_service'] = services[0].get('name')
        else:
            configs['selected_image_service'] = ''
        if services:
            configs['image_service'] = {'base_url': next((s.get('url') for s in services if s.get('name') == configs['selected_image_service']), services[0].get('url'))}
        utils.save_configs(configs)
        return jsonify({
            "success": True,
            "services": configs.get('image_services', []),
            "selected": configs.get('selected_image_service', '')
        })
    return jsonify({
        "services": configs.get('image_services', []),
        "selected": configs.get('selected_image_service', '')
    })


# @app.route('/api/test/openai-model', methods=['POST'])
def test_openai_model():
    return jsonify(test_openai_model_config(request.json or {}))


# @app.route('/api/test/image-service', methods=['POST'])
def test_image_service():
    data = request.json or {}
    service_type = str(data.get('service_type') or 'zimage').strip() or 'zimage'
    return jsonify(test_image_service_url_by_type(data.get('url'), service_type))

# @app.route('/api/config/sampling', methods=['GET', 'POST'])
def manage_sampling_params():
    configs = utils.get_configs()
    if request.method == 'POST':
        new_params = request.json or {}
        configs['sampling_params'] = {
            "temperature": float(new_params.get('temperature', 0.7)),
            "top_p": float(new_params.get('top_p', 0.9)),
            "top_k": int(new_params.get('top_k', 40))
        }
        utils.save_configs(configs)
        return jsonify({"success": True})
    return jsonify(configs.get('sampling_params', {"temperature": 0.7, "top_p": 0.9, "top_k": 40}))

# @app.route('/api/utils/count_tokens', methods=['POST'])
def count_tokens():
    data = request.json
    messages = data.get('messages', [])
    counts = utils.count_messages_tokens(messages)
    return jsonify(counts)

# @app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    model_info = data.get('model_info', {})
    enable_thinking = data.get('enable_thinking', False)
    include_thinking = data.get('include_thinking', False)
    preload = data.get('preload', {}) # Add preload text here
    sampling_params = data.get('sampling_params')

    source = model_info.get('source', 'OpenAI')
    model_display_name = model_info.get('name')
    
    enable_preload = data.get('enable_preload', False)
    
    # Inject preload into the first message or system prompt
    preload_text = ""
    if enable_preload:
        if preload.get('character'): preload_text += f"\n角色设定：{preload['character']}"
        if preload.get('template'): preload_text += f"\n要求：{preload['template']}"
    
    if preload_text and messages:
        messages[0]['text'] += preload_text

    if not include_thinking:
        for m in messages:
            if 'text' in m:
                m['text'] = utils.strip_think_tags(m['text'])

    if source == "Ollama":
        if not sampling_params:
            sampling_params = utils.get_configs().get('sampling_params', {"temperature": 0.7, "top_p": 0.9, "top_k": 40})
        return Response(generate_ollama(messages, model_display_name, sampling_params), mimetype='text/event-stream')
    else:
        # Find model config for OpenAI
        configs = utils.get_configs()
        model_cfg = next((m for m in configs.get('openai_models', []) if m['name'] == model_display_name), None)
        if not model_cfg and configs.get('openai_models'):
            model_cfg = configs['openai_models'][0]
            
        if not model_cfg:
            return jsonify({"error": "No OpenAI model configured"}), 400
            
        client = OpenAI(api_key="EMPTY", base_url=model_cfg['url'])
        if not sampling_params:
            sampling_params = configs.get('sampling_params', {"temperature": 0.7, "top_p": 0.9, "top_k": 40})
        return Response(generate_vllm(client, messages, model_cfg['model_name'], enable_thinking, sampling_params), mimetype='text/event-stream')


def prompt_agent_rewrite():
    data = request.json or {}
    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    preload = data.get('preload', {})
    enable_preload = data.get('enable_preload', False)
    model_info = data.get('model_info', {})
    sampling_params = data.get('sampling_params')
    enable_thinking = data.get('enable_thinking', False)

    if enable_preload:
        preload_parts = []
        if preload.get('character'):
            preload_parts.append(f"角色设定：\n{preload['character']}")
        if preload.get('template'):
            preload_parts.append(f"模板要求：\n{preload['template']}")
        if preload_parts:
            prompt = f"{prompt}\n\n补充预载信息：\n" + "\n\n".join(preload_parts)

    source = model_info.get('source', 'OpenAI')
    model_display_name = model_info.get('name')
    configs = utils.get_configs()
    if not sampling_params:
        sampling_params = configs.get('sampling_params', {"temperature": 0.7, "top_p": 0.9, "top_k": 40})

    try:
        if source == "Ollama":
            result = rewrite_prompt_ollama(prompt, model_display_name, sampling_params)
        else:
            model_cfg = next((m for m in configs.get('openai_models', []) if m['name'] == model_display_name), None)
            if not model_cfg and configs.get('openai_models'):
                model_cfg = configs['openai_models'][0]
            if not model_cfg:
                return jsonify({"error": "No OpenAI model configured"}), 400
            client = OpenAI(api_key="EMPTY", base_url=model_cfg['url'])
            result = rewrite_prompt_vllm(client, prompt, model_cfg['model_name'], enable_thinking, sampling_params)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 502


def scenario_event(event_type, payload=None):
    return f"data: {json.dumps({'type': event_type, **(payload or {})}, ensure_ascii=False)}\n\n"


def scenario_games():
    project = get_current_project(request)
    if request.method == 'POST':
        data = request.json or {}
        game_id = scenario_service.create_game(project, data.get('title') or '未命名剧本')
        return jsonify({'ok': True, 'game_id': game_id})
    return jsonify({'ok': True, 'games': scenario_service.list_games(project)})


def scenario_game_detail(game_id):
    project = get_current_project(request)
    if request.method == 'GET':
        state = scenario_service.get_game_state(project, game_id)
        if not state:
            return jsonify({'ok': False, 'error': 'game not found'}), 404
        return jsonify({'ok': True, **state})
    if request.method == 'PUT':
        ok = scenario_service.update_game(project, game_id, request.json or {})
        if not ok:
            return jsonify({'ok': False, 'error': 'game not found'}), 404
        return jsonify({'ok': True})
    scenario_service.delete_game(project, game_id)
    return jsonify({'ok': True})


def scenario_save_roles(game_id):
    project = get_current_project(request)
    scenario_service.save_roles(project, game_id, (request.json or {}).get('roles', []))
    return jsonify({'ok': True})


def scenario_reorder_roles(game_id):
    project = get_current_project(request)
    role_ids = (request.json or {}).get('role_ids', [])
    if not scenario_service.reorder_roles(project, game_id, role_ids):
        return jsonify({'ok': False, 'error': 'game or roles not found'}), 404
    return jsonify({'ok': True})


def scenario_start_game(game_id):
    project = get_current_project(request)
    if not scenario_service.start_game(project, game_id):
        return jsonify({'ok': False, 'error': 'game not found'}), 404
    return jsonify({'ok': True})


def scenario_human_action(game_id):
    project = get_current_project(request)
    if not scenario_service.submit_human_action(project, game_id, request.json or {}):
        return jsonify({'ok': False, 'error': 'role or game not found'}), 404
    return jsonify({'ok': True})


def scenario_commit_turn(game_id):
    project = get_current_project(request)
    final_resolution = (request.json or {}).get('final_resolution', '')
    if not scenario_service.commit_turn(project, game_id, final_resolution):
        return jsonify({'ok': False, 'error': 'final_resolution is empty or game not found'}), 400
    return jsonify({'ok': True})


def scenario_clear_summary(game_id):
    project = get_current_project(request)
    scenario_service.clear_summary(project, game_id)
    return jsonify({'ok': True})


def scenario_reset_progress(game_id):
    project = get_current_project(request)
    if not scenario_service.reset_game_progress(project, game_id):
        return jsonify({'ok': False, 'error': 'game not found'}), 404
    return jsonify({'ok': True})


def scenario_clear_board(game_id):
    project = get_current_project(request)
    if not scenario_service.clear_current_turn_board(project, game_id):
        return jsonify({'ok': False, 'error': 'game not found'}), 404
    return jsonify({'ok': True})


def scenario_stream_run(game_id):
    project = get_current_project(request)
    data = request.json or {}
    step = data.get('step')
    model_info = data.get('model_info') or {}
    enable_thinking = bool(data.get('enable_thinking'))

    @stream_with_context
    def generate():
        try:
            state = scenario_service.get_game_state(project, game_id)
            if not state:
                yield scenario_event('error', {'message': 'game not found'})
                return

            game = state['game']
            turn = state['turn']
            yield scenario_event('status', {'message': f"第 {game['current_turn']} 回合开始"})

            if step == 'generate_ai_actions':
                generated = []
                roles = state['roles']
                if not [role for role in roles if not role.get('is_human')]:
                    yield scenario_event('status', {'message': '没有需要自动生成行动的 AI 角色'})
                existing_actions = {
                    action.get('role_id'): action
                    for action in scenario_service.fetch_actions(project, game_id, game['current_turn'])
                }
                prior_actions = []
                for role in roles:
                    if role.get('is_human'):
                        existing = existing_actions.get(role.get('id'))
                        if existing:
                            prior_actions.append(existing)
                        continue
                    yield scenario_event('section', {'title': f"{role['name']} 的行动"})
                    chunks = []
                    try:
                        messages = scenario_service.role_action_messages_with_turn_context(game, role, prior_actions)
                        for chunk in scenario_service.stream_chat_completion(messages, model_info, temperature=0.9, enable_thinking=enable_thinking):
                            chunks.append(chunk)
                            yield scenario_event('delta', {'text': chunk})
                        raw = ''.join(chunks).strip()
                        result = scenario_service.save_ai_action(project, game_id, game['current_turn'], role, raw)
                        generated.append(result)
                        prior_actions.append({
                            'role_id': role.get('id'),
                            'role_name': role.get('name'),
                            'speech': result.get('speech', ''),
                            'action': result.get('action', ''),
                            'source': 'ai',
                        })
                        yield scenario_event('result', {'message': f"{role['name']} 行动已进入 on hold", 'result': result})
                    except Exception as e:
                        error_text = f"【AI 行动生成失败：{e}】"
                        result = scenario_service.save_ai_action(project, game_id, game['current_turn'], role, error_text)
                        generated.append(result)
                        prior_actions.append({
                            'role_id': role.get('id'),
                            'role_name': role.get('name'),
                            'speech': result.get('speech', ''),
                            'action': result.get('action', ''),
                            'source': 'ai',
                        })
                        yield scenario_event('error', {'message': f"{role['name']} 生成失败：{e}"})
                yield scenario_event('done', {'generated': generated})
                return

            if step == 'resolve_turn':
                actions = scenario_service.fetch_actions(project, game_id, game['current_turn'])
                if not actions:
                    yield scenario_event('error', {'message': '当前回合没有 on hold 行动'})
                    return
                yield scenario_event('section', {'title': '管理员结算'})
                chunks = []
                messages = scenario_service.resolution_messages(game, turn, actions, state['roles'])
                for chunk in scenario_service.stream_chat_completion(messages, model_info, temperature=0.75, enable_thinking=enable_thinking):
                    chunks.append(chunk)
                    yield scenario_event('delta', {'text': chunk})
                resolution = ''.join(chunks).strip()
                scenario_service.save_resolution(project, game_id, game['current_turn'], resolution)
                yield scenario_event('done', {'resolution': resolution})
                return

            if step == 'narrate_turn':
                adjudication = (data.get('adjudication') or turn.get('pending_resolution') or '').strip()
                if not adjudication:
                    yield scenario_event('error', {'message': '请先完成并审核管理员裁定内容'})
                    return
                yield scenario_event('section', {'title': '主故事线正文草稿'})
                chunks = []
                messages = scenario_service.narrative_messages(game, turn, state['roles'], adjudication)
                for chunk in scenario_service.stream_chat_completion(messages, model_info, temperature=0.7, enable_thinking=enable_thinking):
                    chunks.append(chunk)
                    yield scenario_event('delta', {'text': chunk})
                narrative = ''.join(chunks).strip()
                scenario_service.save_narrative_draft(project, game_id, game['current_turn'], narrative)
                yield scenario_event('done', {'narrative': narrative})
                return

            if step == 'summarize':
                yield scenario_event('section', {'title': '压缩主故事线'})
                chunks = []
                messages = scenario_service.summary_messages(game)
                for chunk in scenario_service.stream_chat_completion(messages, model_info, temperature=0.3, enable_thinking=enable_thinking):
                    chunks.append(chunk)
                    yield scenario_event('delta', {'text': chunk})
                summary = ''.join(chunks).strip()
                scenario_service.save_summary(project, game_id, summary)
                yield scenario_event('done', {'summary': summary})
                return

            yield scenario_event('error', {'message': 'Unknown step'})
        except Exception as e:
            yield scenario_event('error', {'message': str(e)})

    response = Response(generate(), content_type='text/event-stream; charset=utf-8')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


def register_routes(app):
    app.add_url_rule('/', view_func=index)
    app.add_url_rule('/gallery/<project>/<name>', view_func=gallery)
    app.add_url_rule('/api/projects', methods=['GET'], view_func=get_projects)
    app.add_url_rule('/api/project', methods=['POST'], view_func=create_project)
    app.add_url_rule('/api/data/<data_type>', methods=['GET'], view_func=get_data)
    app.add_url_rule('/api/data/<data_type>', methods=['POST'], view_func=add_data)
    app.add_url_rule('/api/data/<data_type>/<name>', methods=['PUT'], view_func=update_data)
    app.add_url_rule('/api/data/<data_type>/<name>', methods=['DELETE'], view_func=delete_data)
    app.add_url_rule('/api/gallery', methods=['GET'], view_func=get_gallery)
    app.add_url_rule('/api/gallery/<scope>', methods=['DELETE'], view_func=delete_gallery_item)
    app.add_url_rule('/api/image-service/health', methods=['GET'], view_func=image_service_health)
    app.add_url_rule('/api/image-service/generate', methods=['POST'], view_func=image_service_generate)
    app.add_url_rule('/api/image-service/generate_async', methods=['POST'], view_func=image_service_generate_async)
    app.add_url_rule('/api/image-service/progress/<job_id>', methods=['GET'], view_func=image_service_progress)
    app.add_url_rule('/api/image-service/result/<job_id>', methods=['GET'], view_func=image_service_result)
    app.add_url_rule('/api/dialogs', methods=['GET'], view_func=get_dialogs)
    app.add_url_rule('/api/dialogs/<dialog_id>', methods=['POST'], view_func=save_dialog)
    app.add_url_rule('/api/dialogs/<dialog_id>', methods=['DELETE'], view_func=delete_dialog)
    app.add_url_rule('/api/upload', methods=['POST'], view_func=upload_file)
    app.add_url_rule('/static/projects/<project>/resource/<path:resource_path>', view_func=serve_project_file)
    app.add_url_rule('/api/system/backup', methods=['POST'], view_func=backup_system)
    app.add_url_rule('/api/system/export', methods=['GET'], view_func=export_system)
    app.add_url_rule('/models', methods=['GET'], view_func=get_models)
    app.add_url_rule('/api/config/models', methods=['GET', 'POST'], view_func=manage_openai_models)
    app.add_url_rule('/api/config/image-services', methods=['GET', 'POST'], view_func=manage_image_services)
    app.add_url_rule('/api/prompt-agent/rewrite', methods=['POST'], view_func=prompt_agent_rewrite)
    app.add_url_rule('/api/test/openai-model', methods=['POST'], view_func=test_openai_model)
    app.add_url_rule('/api/test/image-service', methods=['POST'], view_func=test_image_service)
    app.add_url_rule('/api/config/sampling', methods=['GET', 'POST'], view_func=manage_sampling_params)
    app.add_url_rule('/api/utils/count_tokens', methods=['POST'], view_func=count_tokens)
    app.add_url_rule('/chat', methods=['POST'], view_func=chat)
    app.add_url_rule('/api/scenario/games', methods=['GET', 'POST'], view_func=scenario_games)
    app.add_url_rule('/api/scenario/games/<int:game_id>', methods=['GET', 'PUT', 'DELETE'], view_func=scenario_game_detail)
    app.add_url_rule('/api/scenario/games/<int:game_id>/roles', methods=['POST'], view_func=scenario_save_roles)
    app.add_url_rule('/api/scenario/games/<int:game_id>/role-order', methods=['POST'], view_func=scenario_reorder_roles)
    app.add_url_rule('/api/scenario/games/<int:game_id>/start', methods=['POST'], view_func=scenario_start_game)
    app.add_url_rule('/api/scenario/games/<int:game_id>/human_action', methods=['POST'], view_func=scenario_human_action)
    app.add_url_rule('/api/scenario/games/<int:game_id>/commit_turn', methods=['POST'], view_func=scenario_commit_turn)
    app.add_url_rule('/api/scenario/games/<int:game_id>/clear_summary', methods=['POST'], view_func=scenario_clear_summary)
    app.add_url_rule('/api/scenario/games/<int:game_id>/reset_progress', methods=['POST'], view_func=scenario_reset_progress)
    app.add_url_rule('/api/scenario/games/<int:game_id>/clear_board', methods=['POST'], view_func=scenario_clear_board)
    app.add_url_rule('/api/scenario/games/<int:game_id>/run', methods=['POST'], view_func=scenario_stream_run)
