from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app_modules.config import PORT
from app_modules.routes import register_routes


def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    register_routes(app)
    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=PORT, debug=True)
