from sqlalchemy import inspect, text

from . import db
from werkzeug.security import generate_password_hash

import json

from .models import EvaluationRecord, EvaluationScheme, Indicator, SchemeMembership, SystemSetting, User


def run_compatibility_migrations():
    """Apply additive SQLite migrations while preserving existing local data."""
    inspector = inspect(db.engine)
    additions = {
        'user': ('scheme_id', 'INTEGER REFERENCES evaluation_scheme(id)'),
        'academic_year': ('scheme_id', 'INTEGER REFERENCES evaluation_scheme(id)'),
        'evaluation_record': ('scheme_id', 'INTEGER REFERENCES evaluation_scheme(id)'),
    }
    for table, (column, definition) in additions.items():
        if table not in inspector.get_table_names():
            continue
        columns = {item['name'] for item in inspector.get_columns(table)}
        if column not in columns:
            db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {definition}'))
            db.session.commit()

    inspector = inspect(db.engine)
    extra_additions = {
        'evaluation_scheme': [('owner_user_id', 'INTEGER REFERENCES user(id)')],
        'academic_year': [('display_name', 'VARCHAR(50)')],
    }
    for table, columns_to_add in extra_additions.items():
        if table not in inspector.get_table_names():
            continue
        columns = {item['name'] for item in inspector.get_columns(table)}
        for column, definition in columns_to_add:
            if column not in columns:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {definition}'))
                db.session.commit()

    scheme = EvaluationScheme.query.order_by(EvaluationScheme.id).first()
    if scheme is None:
        scheme = EvaluationScheme(
            code='DEFAULT-001',
            name='默认校园评价方案',
            description='由旧版数据自动迁移创建。',
            status='active',
        )
        db.session.add(scheme)
        db.session.commit()

    db.session.execute(text('UPDATE user SET scheme_id = :sid WHERE scheme_id IS NULL'), {'sid': scheme.id})
    db.session.execute(text('UPDATE academic_year SET scheme_id = :sid WHERE scheme_id IS NULL'), {'sid': scheme.id})
    db.session.execute(text('UPDATE evaluation_record SET scheme_id = :sid WHERE scheme_id IS NULL'), {'sid': scheme.id})
    db.session.commit()

    # v0.2.5：档案的二级跟踪维度统一为“班级”。旧版曾把学生姓名写入
    # secondary_tracking_value，导致学生姓名混入班级下拉框。迁移时保留姓名，
    # 将其移到该指标的普通填报字段中；班级需由教师在待审核记录中补填。
    for indicator in Indicator.query.filter_by(code='student_award_bonus').all():
        try:
            rule = json.loads(indicator.scoring_rule_json or '{}')
        except json.JSONDecodeError:
            rule = {}
        extra_fields = rule.setdefault('extra_fields', [])
        if not any(item.get('key') == 'student_name' for item in extra_fields if isinstance(item, dict)):
            extra_fields.append({
                'key': 'student_name', 'label': '学生姓名', 'input_type': 'text', 'required': True,
            })
        indicator.scoring_rule_json = json.dumps(rule, ensure_ascii=False)

        try:
            tracking = json.loads(indicator.secondary_tracking_json or '{}')
        except json.JSONDecodeError:
            tracking = {}
        if tracking.get('label') == '学生姓名':
            for record in EvaluationRecord.query.filter_by(indicator_id=indicator.id).all():
                try:
                    inputs = json.loads(record.input_json or '{}')
                except json.JSONDecodeError:
                    inputs = {}
                if record.secondary_tracking_value and not inputs.get('student_name'):
                    inputs['student_name'] = record.secondary_tracking_value
                record.input_json = json.dumps(inputs, ensure_ascii=False)
                record.secondary_tracking_value = None
        indicator.secondary_tracking_json = json.dumps({
            'enabled': True, 'label': '班级', 'required': True, 'input_type': 'text',
        }, ensure_ascii=False)
    db.session.commit()

    # 旧版管理员保留为部门管理员；首次升级额外创建本地超级管理员。
    superadmin = User.query.filter_by(role='superadmin').first()
    legacy_admin = User.query.filter_by(role='admin').order_by(User.id).first()
    if superadmin is None and legacy_admin is not None:
        username = 'superadmin'
        suffix = 1
        while User.query.filter_by(username=username).first():
            suffix += 1
            username = f'superadmin{suffix}'
        superadmin = User(
            username=username, display_name='超级管理员', role='superadmin',
            password_hash=generate_password_hash('123456'), is_homeroom_teacher=False,
            scheme_id=scheme.id,
        )
        db.session.add(superadmin)
        db.session.commit()

    # 为旧数据补齐方案负责人和账号成员关系。
    for item in EvaluationScheme.query.order_by(EvaluationScheme.id).all():
        if item.owner_user_id is None:
            owner = User.query.filter_by(role='admin', scheme_id=item.id).order_by(User.id).first()
            if owner:
                item.owner_user_id = owner.id
        users = User.query.filter(User.scheme_id == item.id, User.role.in_(['admin', 'reviewer', 'teacher'])).all()
        for user in users:
            if not SchemeMembership.query.filter_by(scheme_id=item.id, user_id=user.id).first():
                role = 'owner' if item.owner_user_id == user.id else ('reviewer' if user.role == 'reviewer' else 'participant')
                db.session.add(SchemeMembership(scheme_id=item.id, user_id=user.id, membership_role=role))
    update_source = db.session.get(SystemSetting, 'update_base_url')
    if update_source is None:
        db.session.add(SystemSetting(
            key='update_base_url', value='http://121.199.56.216/campus-evaluation/updates',
        ))
    elif not update_source.value.strip():
        update_source.value = 'http://121.199.56.216/campus-evaluation/updates'
    db.session.commit()
