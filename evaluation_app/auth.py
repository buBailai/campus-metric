from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import AcademicYear, AuditLog, EvaluationScheme, SchemeMembership, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.first():
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        password = request.form.get('password', '')
        academic_year = request.form.get('academic_year', '').strip()
        if not username or not display_name or not academic_year:
            flash('请填写完整的管理员和学年信息。', 'danger')
        elif len(password) < 8:
            flash('管理员密码至少需要8个字符。', 'danger')
        else:
            scheme = EvaluationScheme.query.filter_by(status='active').order_by(EvaluationScheme.id).first()
            if scheme is None:
                scheme = EvaluationScheme(
                    code='DEFAULT-001', name='默认校园评价方案',
                    description='首次初始化自动创建。', status='active',
                )
                db.session.add(scheme)
                db.session.flush()
            user = User(
                username=username,
                display_name=display_name,
                password_hash=generate_password_hash(password),
                role='superadmin',
                scheme_id=scheme.id if scheme else None,
                is_homeroom_teacher=False,
            )
            year = AcademicYear(name=academic_year, status='active', scheme_id=scheme.id if scheme else None)
            db.session.add_all([user, year])
            db.session.flush()
            scheme.owner_user_id = user.id
            db.session.add(SchemeMembership(scheme_id=scheme.id, user_id=user.id, membership_role='owner'))
            db.session.add(AuditLog(
                user_id=user.id,
                action='system.setup',
                entity_type='academic_year',
                entity_id=str(year.id),
                detail_json='{}',
            ))
            db.session.commit()
            login_user(user)
            return redirect(url_for('main.dashboard'))
    return render_template('setup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if not User.query.first():
        return redirect(url_for('auth.setup'))
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username, is_active_flag=True).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=False)
            db.session.add(AuditLog(
                user_id=user.id,
                action='auth.login',
                entity_type='user',
                entity_id=str(user.id),
                detail_json='{}',
            ))
            db.session.commit()
            next_url = request.form.get('next', '').strip()
            if next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect(url_for('main.dashboard'))
        flash('账号或密码错误。', 'danger')
    return render_template('login.html', next_url=request.args.get('next', ''))


@auth_bp.route('/logout', methods=['POST'])
def logout():
    if current_user.is_authenticated:
        user_id = current_user.id
        logout_user()
        db.session.add(AuditLog(
            user_id=user_id,
            action='auth.logout',
            entity_type='user',
            entity_id=str(user_id),
            detail_json='{}',
            created_at=datetime.now(),
        ))
        db.session.commit()
    return redirect(url_for('auth.login'))
