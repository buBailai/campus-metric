from datetime import datetime

from flask_login import UserMixin

from . import db


class EvaluationScheme(db.Model):
    __tablename__ = 'evaluation_scheme'

    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey('evaluation_scheme.id'))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    employee_no = db.Column(db.String(50), unique=True)
    role = db.Column(db.String(20), nullable=False, default='teacher')
    is_active_flag = db.Column(db.Boolean, nullable=False, default=True)
    is_homeroom_teacher = db.Column(db.Boolean, nullable=False, default=True)
    is_grade_leader = db.Column(db.Boolean, nullable=False, default=False)
    tenure_years = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    scheme = db.relationship('EvaluationScheme', foreign_keys=[scheme_id])

    @property
    def is_active(self):
        return bool(self.is_active_flag)


class SchemeMembership(db.Model):
    __tablename__ = 'scheme_membership'
    __table_args__ = (db.UniqueConstraint('scheme_id', 'user_id', name='uq_scheme_membership'),)

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey('evaluation_scheme.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    membership_role = db.Column(db.String(20), nullable=False, default='participant')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    scheme = db.relationship('EvaluationScheme', backref=db.backref('memberships', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('scheme_memberships', cascade='all, delete-orphan'))


class AcademicYear(db.Model):
    __tablename__ = 'academic_year'

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey('evaluation_scheme.id'))
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(50))
    starts_on = db.Column(db.Date)
    ends_on = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default='active')
    archived_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    scheme = db.relationship('EvaluationScheme')

    @property
    def label(self):
        return self.display_name or self.name.split(' @ ')[0]


class Category(db.Model):
    __tablename__ = 'category'
    __table_args__ = (db.UniqueConstraint('academic_year_id', 'code', name='uq_category_year_code'),)

    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    code = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    max_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    academic_year = db.relationship('AcademicYear', backref=db.backref('categories', cascade='all, delete-orphan'))
    indicators = db.relationship(
        'Indicator',
        back_populates='category',
        cascade='all, delete-orphan',
        order_by='Indicator.sort_order',
    )


class Indicator(db.Model):
    __tablename__ = 'indicator'
    __table_args__ = (db.UniqueConstraint('academic_year_id', 'code', name='uq_indicator_year_code'),)

    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    code = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    score_group = db.Column(db.String(20), nullable=False, default='base')
    data_source = db.Column(db.String(20), nullable=False, default='admin')
    scoring_type = db.Column(db.String(30), nullable=False)
    scoring_rule_json = db.Column(db.Text, nullable=False, default='{}')
    allow_multiple_records = db.Column(db.Boolean, nullable=False, default=False)
    requires_evidence = db.Column(db.Boolean, nullable=False, default=False)
    ai_enabled = db.Column(db.Boolean, nullable=False, default=False)
    secondary_tracking_json = db.Column(db.Text, nullable=False, default='{"enabled": false}')
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    academic_year = db.relationship('AcademicYear')
    category = db.relationship('Category', back_populates='indicators')


class EvaluationRecord(db.Model):
    __tablename__ = 'evaluation_record'

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey('evaluation_scheme.id'))
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicator.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submitted_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    source = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='draft')
    input_json = db.Column(db.Text, nullable=False, default='{}')
    secondary_tracking_value = db.Column(db.String(200))
    auto_score = db.Column(db.Float)
    final_score = db.Column(db.Float)
    admin_overridden = db.Column(db.Boolean, nullable=False, default=False)
    note = db.Column(db.Text, nullable=False, default='')
    review_note = db.Column(db.Text, nullable=False, default='')
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    academic_year = db.relationship('AcademicYear')
    scheme = db.relationship('EvaluationScheme')
    indicator = db.relationship('Indicator')
    target_user = db.relationship('User', foreign_keys=[target_user_id])
    submitted_by = db.relationship('User', foreign_keys=[submitted_by_user_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_user_id])


class RecordAttachment(db.Model):
    __tablename__ = 'record_attachment'

    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('evaluation_record.id'), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100))
    size_bytes = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    record = db.relationship('EvaluationRecord', backref=db.backref('attachments', cascade='all, delete-orphan'))


class DictionarySnapshot(db.Model):
    __tablename__ = 'dictionary_snapshot'

    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    dictionary_json = db.Column(db.Text, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.String(100))
    detail_json = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class AIModelSetting(db.Model):
    __tablename__ = 'ai_model_setting'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False, default='custom')
    api_base = db.Column(db.String(500), nullable=False, default='')
    api_key = db.Column(db.String(500), nullable=False, default='')
    model_name = db.Column(db.String(200), nullable=False, default='')
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class SystemSetting(db.Model):
    __tablename__ = 'system_setting'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False, default='')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
