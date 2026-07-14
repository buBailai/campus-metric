"""Production entrypoint for mounting the app behind an Nginx URL prefix."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from waitress import serve
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.wrappers import Response

from app import app


def not_found(environ, start_response):
    return Response('Not Found', status=404)(environ, start_response)


prefix = os.getenv('URL_PREFIX', '/campus-evaluation/app').rstrip('/')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
application = DispatcherMiddleware(not_found, {prefix: app})


if __name__ == '__main__':
    serve(
        application,
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', '8135')),
        threads=int(os.getenv('THREADS', '8')),
    )
