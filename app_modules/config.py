import os
import requests

SERVER_IP = "10.88.20.111"
PORT = 15000
TOP_K = 20
WHITE_LIST = ['10.88.21.19', '10.88.21.14', '10.88.21.3', '127.0.0.1','10.1.83.101']

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'projects')
os.makedirs(PROJECTS_DIR, exist_ok=True)

OLLAMA_BASE_URL = "http://10.10.11.31:11434"
IMAGE_SERVICE_BASE_URL = "http://localhost:6000"
IMAGE_SERVICE_SESSION = requests.Session()
IMAGE_SERVICE_SESSION.trust_env = False
