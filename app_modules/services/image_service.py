import base64
import os
import uuid

import requests
from werkzeug.utils import secure_filename

from app_modules.config import IMAGE_SERVICE_BASE_URL, IMAGE_SERVICE_SESSION, PROJECTS_DIR
from app_modules.helpers import get_base64_image
import utils


IMAGE_JOB_PAYLOADS = {}


def get_image_service_url():
    service = get_selected_image_service()
    if service and service.get('url'):
        return service['url'].rstrip('/')
    return IMAGE_SERVICE_BASE_URL.rstrip('/')


def get_image_service_type(service):
    return str((service or {}).get('service_type') or 'zimage').strip() or 'zimage'


def is_hidream_service(service):
    return get_image_service_type(service) == 'hidream_o1'


def get_selected_image_service():
    configs = utils.get_configs()
    services = configs.get('image_services') or []
    selected = configs.get('selected_image_service')
    service = next((s for s in services if s.get('name') == selected), None)
    if service:
        return service
    if services:
        return services[0]
    return {
        'name': 'Image Service',
        'url': configs.get('image_service', {}).get('base_url', IMAGE_SERVICE_BASE_URL),
        'service_type': 'zimage',
        'default_params': {},
        'enabled_params': [],
        'param_types': {}
    }


def get_image_service_by_name(name):
    configs = utils.get_configs()
    services = configs.get('image_services') or []
    service = next((s for s in services if s.get('name') == name), None)
    return service or get_selected_image_service()


def image_service_get(url, **kwargs):
    return IMAGE_SERVICE_SESSION.get(url, **kwargs)


def image_service_post(url, **kwargs):
    return IMAGE_SERVICE_SESSION.post(url, **kwargs)


def test_image_service_url(base_url):
    base_url = (base_url or '').rstrip('/')
    if not base_url:
        return {'online': False, 'error': 'URL is required'}
    try:
        resp = image_service_get(f"{base_url}/health", timeout=3)
        data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
        return {
            'online': resp.ok and data.get('status') == 'ok',
            'status_code': resp.status_code,
            'base_url': base_url,
            'service': data
        }
    except Exception as e:
        return {'online': False, 'base_url': base_url, 'error': str(e)}


def test_image_service_url_by_type(base_url, service_type='zimage'):
    base_url = (base_url or '').rstrip('/')
    if not base_url:
        return {'online': False, 'error': 'URL is required'}
    health_path = '/v1/health' if service_type == 'hidream_o1' else '/health'
    try:
        resp = image_service_get(f"{base_url}{health_path}", timeout=3)
        data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
        online = resp.ok and data.get('status') == 'ok'
        return {
            'online': online,
            'status_code': resp.status_code,
            'base_url': base_url,
            'service_type': service_type,
            'service': data
        }
    except Exception as e:
        return {'online': False, 'base_url': base_url, 'service_type': service_type, 'error': str(e)}


def test_openai_model_config(model_cfg):
    base_url = (model_cfg.get('url') or '').rstrip('/')
    if not base_url:
        return {'online': False, 'error': 'URL is required'}
    try:
        resp = requests.get(f"{base_url}/models", timeout=5)
        data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
        return {
            'online': resp.ok,
            'status_code': resp.status_code,
            'base_url': base_url,
            'models': data.get('data', data.get('models', [])) if isinstance(data, dict) else []
        }
    except Exception as e:
        return {'online': False, 'base_url': base_url, 'error': str(e)}


def save_generated_image(project, image_b64, output_name=None):
    pj_path = utils.ensure_project_structure(PROJECTS_DIR, project)
    resource_root = os.path.join(pj_path, 'resource')
    save_dir = os.path.join(resource_root, 'gen_pic')
    os.makedirs(save_dir, exist_ok=True)

    safe_name = secure_filename(output_name or '')
    if not safe_name:
        safe_name = f"{utils.generate_unique_time_string_with_uuid()}.png"
    if not os.path.splitext(safe_name)[1]:
        safe_name += '.png'

    file_path = os.path.join(save_dir, safe_name)
    if os.path.exists(file_path):
        stem, ext = os.path.splitext(safe_name)
        file_path = os.path.join(save_dir, f"{stem}_{uuid.uuid4().hex[:8]}{ext}")

    if ',' in image_b64 and image_b64.lstrip().startswith('data:'):
        image_b64 = image_b64.split(',', 1)[1]
    with open(file_path, 'wb') as f:
        f.write(base64.b64decode(image_b64))

    media_url = f"/static/projects/{project}/resource/{os.path.relpath(file_path, resource_root).replace(os.sep, '/')}"
    return file_path, media_url


def parse_bool_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if value is None:
        return False
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def normalize_image_param_value(key, value, value_type=None):
    if value_type == 'boolean':
        return parse_bool_value(value)
    if value_type == 'int' or key in ('height', 'width', 'num_inference_steps', 'seed'):
        try:
            numeric = int(float(value))
        except (TypeError, ValueError):
            return None
        if key in ('height', 'width'):
            return normalize_to_multiple(numeric)
        return numeric
    if value_type == 'float' or key == 'guidance_scale':
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if value is None:
        return None
    return str(value)


def remember_image_job_payload(job_id, payload):
    if job_id:
        IMAGE_JOB_PAYLOADS[str(job_id)] = dict(payload or {})


def get_remembered_image_job_payload(job_id):
    return dict(IMAGE_JOB_PAYLOADS.get(str(job_id), {}))


def build_hidream_generation_payload(data):
    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return None

    mode = str(data.get('mode') or 't2i').strip() or 't2i'
    payload = {
        'prompt': prompt,
        'width': normalize_image_param_value('width', data.get('width'), 'int') or 2048,
        'height': normalize_image_param_value('height', data.get('height'), 'int') or 2048,
        'seed': normalize_image_param_value('seed', data.get('seed'), 'int') or 32,
    }
    if mode != 't2i':
        payload['mode'] = mode

    refs_paths = data.get('refs_paths') or []
    refs_b64 = []
    for item in refs_paths:
        file_path = str(item or '').strip()
        if not file_path:
            continue
        encoded = get_base64_image(file_path)
        if encoded:
            refs_b64.append(encoded)
    if mode == 'edit':
        if refs_b64:
            payload['refs_b64'] = refs_b64[:1]
    elif mode == 'subject':
        if refs_b64:
            payload['refs_b64'] = refs_b64

    if mode == 'edit':
        payload['keep_original_aspect'] = parse_bool_value(data.get('keep_original_aspect'))
        editing_scheduler = str(data.get('editing_scheduler') or '').strip()
        if editing_scheduler:
            payload['editing_scheduler'] = editing_scheduler

    params = {}
    for key, value_type in (
        ('num_inference_steps', 'int'),
        ('guidance_scale', 'float'),
        ('shift', 'float'),
    ):
        value = normalize_image_param_value(key, data.get(key), value_type)
        if value is not None:
            params[key] = value
    scheduler_name = str(data.get('scheduler_name') or '').strip()
    if scheduler_name:
        params['scheduler_name'] = scheduler_name
    if params:
        payload['params'] = params

    raw_preview_steps = str(data.get('preview_steps') or '').strip()
    if raw_preview_steps:
        preview_steps = []
        for chunk in raw_preview_steps.split(','):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                preview_steps.append(int(chunk))
            except ValueError:
                continue
        if preview_steps:
            payload['preview_steps'] = preview_steps

    return payload


def build_image_generation_payload(data, service_config=None):
    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return None

    service = service_config or get_selected_image_service()
    if is_hidream_service(service):
        return build_hidream_generation_payload(data)
    default_params = dict(service.get('default_params') or {})
    enabled_params = list(service.get('enabled_params') or default_params.keys())
    param_types = dict(service.get('param_types') or {})

    payload = {'prompt': prompt}
    for key in enabled_params:
        if key == 'prompt':
            continue
        raw_value = data.get(key) if key in data else default_params.get(key)
        normalized = normalize_image_param_value(key, raw_value, param_types.get(key))
        if key == 'output_name':
            if normalized:
                payload[key] = normalized
            continue
        if key == 'attn_backend':
            continue
        if normalized is None:
            continue
        payload[key] = normalized
    return payload


def finalize_generated_result(project, payload, result):
    image_b64 = result.get('base64') or result.get('image')
    if not image_b64:
        return None

    output_name = payload.get('output_name') or os.path.basename(result.get('output_path') or '')
    file_path, media_url = save_generated_image(project, image_b64, output_name)
    service_response = {k: v for k, v in result.items() if k not in ('base64', 'image')}
    return {
        'success': True,
        'url': media_url,
        'path': file_path,
        'params': payload,
        'service_response': service_response
    }


def normalize_to_multiple(value, multiple=16, minimum=16):
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = minimum
    if numeric < minimum:
        numeric = minimum
    lower = (numeric // multiple) * multiple
    upper = lower + multiple
    if numeric - lower < upper - numeric:
        return lower
    return upper

