import os

from dotenv import load_dotenv

from evaluation_app import create_app

load_dotenv()
app = create_app()


if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5012'))
    debug = os.getenv('APP_DEBUG', '').strip().lower() in {'1', 'true', 'yes'}
    if debug:
        app.run(host=host, port=port, debug=True)
    else:
        try:
            from waitress import serve

            serve(app, host=host, port=port, threads=8)
        except ImportError:
            app.run(host=host, port=port, debug=False)
