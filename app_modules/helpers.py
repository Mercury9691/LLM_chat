import base64
import os

from app_modules.config import PROJECTS_DIR
import utils


def get_current_project(req):
    pj = req.headers.get('X-Project')
    if not pj:
        # Default to the first available project, or create 'default'
        folders = utils.get_all_folders(PROJECTS_DIR)
        if not folders:
            pj = 'default'
            utils.ensure_project_structure(PROJECTS_DIR, pj)
        else:
            pj = folders[0]
    return pj


def get_db_path(project):
    pj_path = utils.ensure_project_structure(PROJECTS_DIR, project)
    return os.path.join(pj_path, 'resource', 'database.db')


def get_base64_image(file_path):
    if not os.path.exists(file_path): return ""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def save_uploaded_file(file, save_dir, filename_base):
    os.makedirs(save_dir, exist_ok=True)
    original_ext = file.filename.rsplit('.', 1)[-1].lower()
    if original_ext in ('heic', 'heif'):
        output_filename = f"{filename_base}.jpg"
        out_path = os.path.join(save_dir, output_filename)
        try:
            from PIL import Image
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except ImportError:
                pass
            file.stream.seek(0)
            image = Image.open(file.stream)
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')
            image.save(out_path, format='JPEG', quality=90)
            return out_path, output_filename
        except Exception:
            file.stream.seek(0)
            fallback_filename = f"{filename_base}.{original_ext}"
            out_path = os.path.join(save_dir, fallback_filename)
            file.save(out_path)
            return out_path, fallback_filename
    else:
        output_filename = f"{filename_base}.{original_ext}"
        out_path = os.path.join(save_dir, output_filename)
        file.save(out_path)
        return out_path, output_filename

