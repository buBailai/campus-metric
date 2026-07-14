import os
import secrets
import sys
from pathlib import Path

_vendor_dir = Path(__file__).resolve().parent.parent / 'vendor'
if _vendor_dir.is_dir() and str(_vendor_dir) not in sys.path:
    sys.path.insert(0, str(_vendor_dir))

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(test_config=None):
    base_dir = Path(__file__).resolve().parent.parent
    instance_dir = base_dir / 'instance'
    upload_dir = base_dir / 'uploads'
    instance_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(
        __name__,
        instance_path=str(instance_dir),
        template_folder=str(base_dir / 'templates'),
        static_folder=str(base_dir / 'static'),
    )
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_urlsafe(48),
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', f"sqlite:///{instance_dir / 'evaluation.sqlite'}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
        UPLOAD_FOLDER=str(upload_dir),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录系统。'

    from .models import AcademicYear, EvaluationScheme, SchemeMembership, User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_active_year():
        from flask_login import current_user
        from .dictionary_service import current_scheme, current_year
        scheme = current_scheme()
        year = current_year()
        schemes = []
        if current_user.is_authenticated:
            query = EvaluationScheme.query
            if current_user.role == 'admin':
                member_ids = db.session.query(SchemeMembership.scheme_id).filter_by(user_id=current_user.id)
                query = query.filter(db.or_(EvaluationScheme.owner_user_id == current_user.id, EvaluationScheme.id.in_(member_ids)))
            elif current_user.role in {'reviewer', 'teacher'}:
                member_ids = db.session.query(SchemeMembership.scheme_id).filter_by(user_id=current_user.id)
                query = query.filter(db.or_(EvaluationScheme.id.in_(member_ids), EvaluationScheme.id == current_user.scheme_id))
            schemes = query.order_by(EvaluationScheme.id).all()
        return {'active_year': year, 'active_scheme': scheme, 'accessible_schemes': schemes}

    @app.template_filter('score')
    def format_score(value):
        if value is None:
            return '—'
        number = float(value)
        return f'{number:.1f}'.rstrip('0').rstrip('.')

    from .auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        from .migrations import run_compatibility_migrations
        run_compatibility_migrations()

    return app
