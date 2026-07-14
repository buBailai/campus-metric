import json
import re
from collections import Counter

from flask import has_request_context, session
from flask_login import current_user

from . import db
from .models import AcademicYear, Category, DictionarySnapshot, EvaluationRecord, EvaluationScheme, Indicator, SchemeMembership

SCHEMA_VERSION = '1.0'
SCORE_GROUPS = {'base', 'bonus', 'deduction'}
DATA_SOURCES = {'teacher', 'admin', 'excel'}
SCORING_TYPES = {
    'manual_score', 'fixed_score', 'tiered_score', 'count_score',
    'count_deduction', 'range_score', 'matrix_score', 'tenure_score', 'fixed_bonus',
}
CODE_RE = re.compile(r'^[a-z][a-z0-9_-]{1,63}$')


def current_scheme():
    query = EvaluationScheme.query
    if has_request_context() and current_user.is_authenticated:
        if current_user.role == 'admin':
            member_ids = db.session.query(SchemeMembership.scheme_id).filter_by(user_id=current_user.id)
            query = query.filter(
                db.or_(EvaluationScheme.owner_user_id == current_user.id, EvaluationScheme.id.in_(member_ids))
            )
        elif current_user.role in {'reviewer', 'teacher'}:
            member_ids = db.session.query(SchemeMembership.scheme_id).filter_by(user_id=current_user.id)
            query = query.filter(db.or_(EvaluationScheme.id.in_(member_ids), EvaluationScheme.id == current_user.scheme_id))
        selected_id = session.get('active_scheme_id')
        if selected_id:
            selected = query.filter(EvaluationScheme.id == selected_id).first()
            if selected:
                return selected
        if current_user.scheme_id:
            selected = query.filter(EvaluationScheme.id == current_user.scheme_id).first()
            if selected:
                return selected
    return query.filter_by(status='active').order_by(EvaluationScheme.id).first() or query.order_by(EvaluationScheme.id).first()


def current_year():
    scheme = current_scheme()
    query = AcademicYear.query.filter_by(status='active')
    if scheme:
        query = query.filter_by(scheme_id=scheme.id)
    return query.order_by(AcademicYear.id.desc()).first()


def blank_template():
    return {
        'schema_version': SCHEMA_VERSION,
        'dictionary_name': '校园评价字典',
        'description': '原方案未明确处请在description中标记“待管理员确认”',
        'categories': [{
            'code': 'category_code', 'name': '一级指标名称', 'description': '',
            'order': 1, 'max_score': None,
            'items': [{
                'code': 'item_code', 'name': '考评明细名称', 'description': '考评要求和计分说明',
                'order': 1, 'score_group': 'base', 'data_source': 'admin',
                'scoring_type': 'manual_score',
                'scoring_rule': {'min_score': 0, 'max_score': 5},
                'allow_multiple_records': False, 'requires_evidence': False,
                'ai_enabled': False,
                'secondary_tracking': {
                    'enabled': True, 'label': '班级', 'required': True,
                    'input_type': 'select', 'options': [],
                },
                'enabled': True,
            }],
        }],
    }


def full_example():
    def entry(code, name, scoring_type, rule, source='admin', group='base', evidence=False):
        return {
            'code': code, 'name': name, 'description': '', 'order': 1,
            'score_group': group, 'data_source': source, 'scoring_type': scoring_type,
            'scoring_rule': rule, 'allow_multiple_records': source == 'teacher',
            'requires_evidence': evidence, 'ai_enabled': evidence,
            'secondary_tracking': {'enabled': False}, 'enabled': True,
        }

    return {
        'schema_version': SCHEMA_VERSION,
        'dictionary_name': '校园评价字典完整示例',
        'description': '展示首版支持的全部积分类型',
        'categories': [{
            'code': 'example_category', 'name': '示例一级指标', 'description': '',
            'order': 1, 'max_score': None,
            'items': [
                entry('manual', '管理员直接给分', 'manual_score', {'min_score': 0, 'max_score': 5}),
                entry('fixed', '固定分值', 'fixed_score', {'score': 2}, 'teacher', 'base', True),
                entry('tiered', '分档计分', 'tiered_score', {'options': [
                    {'value': 'excellent', 'label': '优秀', 'score': 10},
                    {'value': 'good', 'label': '良好', 'score': 8},
                ]}),
                entry('count_add', '按次数加分', 'count_score', {
                    'score_per_count': 2, 'min_score': 0, 'max_score': 10,
                }, 'teacher', 'bonus', True),
                entry('count_minus', '按次数扣分', 'count_deduction', {
                    'initial_score': 5, 'score_per_count': 1, 'max_deduction': 5,
                    'min_score': 0, 'max_score': 5,
                }),
                entry('range', '数值区间计分', 'range_score', {'ranges': [
                    {'min': 90, 'max': None, 'min_inclusive': True, 'max_inclusive': True, 'score': 5},
                    {'min': 80, 'max': 90, 'min_inclusive': True, 'max_inclusive': False, 'score': 4},
                ]}, 'excel'),
                entry('matrix', '级别和奖次二维查表', 'matrix_score', {
                    'level_field': 'level', 'rank_field': 'rank',
                    'scores': [
                        {'level': 'district', 'level_label': '区级', 'rank': 'first', 'rank_label': '一等奖', 'score': 3},
                        {'level': 'district', 'level_label': '区级', 'rank': 'second', 'rank_label': '二等奖', 'score': 2},
                    ],
                }, 'teacher', 'bonus', True),
                entry('tenure', '按任职年限分档', 'tenure_score', {'tiers': [
                    {'min_years': 10, 'score': 2}, {'min_years': 15, 'score': 4},
                ]}, group='bonus'),
                entry('leader', '兼任年段长加分', 'fixed_bonus', {'score': 20}, group='bonus'),
            ],
        }],
    }


def validate_dictionary(data):
    errors, warnings = [], []
    counts = Counter()

    def error(path, message):
        errors.append({'path': path, 'message': message})

    def warning(path, message):
        warnings.append({'path': path, 'message': message})

    if not isinstance(data, dict):
        return {'valid': False, 'errors': [{'path': '$', 'message': '顶层内容必须是JSON对象'}], 'warnings': [], 'summary': {}}
    if data.get('schema_version') != SCHEMA_VERSION:
        error('schema_version', f'只支持模板版本 {SCHEMA_VERSION}')
    if not str(data.get('dictionary_name') or '').strip():
        error('dictionary_name', '不能为空')
    categories = data.get('categories')
    if not isinstance(categories, list):
        error('categories', '必须是数组')
        return _validation_result(errors, warnings, counts)

    category_codes, item_codes = set(), set()
    for ci, category in enumerate(categories):
        path = f'categories[{ci}]'
        if not isinstance(category, dict):
            error(path, '一级指标必须是对象')
            continue
        _validate_code(category.get('code'), f'{path}.code', category_codes, error)
        if not str(category.get('name') or '').strip():
            error(f'{path}.name', '不能为空')
        if category.get('max_score') is not None and not _number(category.get('max_score')):
            error(f'{path}.max_score', '必须是有效数字或null')
        items = category.get('items')
        if not isinstance(items, list):
            error(f'{path}.items', '必须是数组')
            continue
        counts['categories'] += 1
        if not items:
            warning(f'{path}.items', '该一级指标没有考评明细')
        for ii, item in enumerate(items):
            item_path = f'{path}.items[{ii}]'
            if not isinstance(item, dict):
                error(item_path, '考评明细必须是对象')
                continue
            _validate_code(item.get('code'), f'{item_path}.code', item_codes, error)
            if not str(item.get('name') or '').strip():
                error(f'{item_path}.name', '不能为空')
            if item.get('score_group') not in SCORE_GROUPS:
                error(f'{item_path}.score_group', '只允许 base、bonus 或 deduction')
            if item.get('data_source') not in DATA_SOURCES:
                error(f'{item_path}.data_source', '只允许 teacher、admin 或 excel')
            scoring_type = item.get('scoring_type')
            if scoring_type not in SCORING_TYPES:
                error(f'{item_path}.scoring_type', '不支持该积分类型')
            for flag in ('allow_multiple_records', 'requires_evidence', 'ai_enabled', 'enabled'):
                if not isinstance(item.get(flag), bool):
                    error(f'{item_path}.{flag}', '必须是true或false')
            if item.get('ai_enabled') and not item.get('requires_evidence'):
                warning(f'{item_path}.ai_enabled', '已启用AI识别，但未要求上传证明材料')
            _validate_secondary(item.get('secondary_tracking'), f'{item_path}.secondary_tracking', error, warning)
            _validate_rule(scoring_type, item.get('scoring_rule'), f'{item_path}.scoring_rule', error)
            counts['items'] += 1
            counts[f'source:{item.get("data_source")}'] += 1
            counts[f'type:{scoring_type}'] += 1
    return _validation_result(errors, warnings, counts)


def _validation_result(errors, warnings, counts):
    return {
        'valid': not errors,
        'errors': errors,
        'warnings': warnings,
        'summary': {
            'categories': counts['categories'], 'items': counts['items'],
            'teacher_items': counts['source:teacher'], 'admin_items': counts['source:admin'],
            'excel_items': counts['source:excel'],
            'scoring_types': {key.split(':', 1)[1]: value for key, value in counts.items() if key.startswith('type:')},
        },
    }


def _validate_code(value, path, used, error):
    if not isinstance(value, str) or not CODE_RE.fullmatch(value):
        error(path, '编码须以小写字母开头，只能包含小写字母、数字、下划线或短横线，长度2—64位')
        return
    if value in used:
        error(path, f'编码 {value} 重复')
    used.add(value)


def _validate_secondary(value, path, error, warning):
    if not isinstance(value, dict):
        error(path, '必须是对象')
        return
    if not isinstance(value.get('enabled'), bool):
        error(f'{path}.enabled', '必须是true或false')
        return
    if not value.get('enabled'):
        return
    if not str(value.get('label') or '').strip():
        error(f'{path}.label', '启用后必须填写字段名称')
    if value.get('input_type') not in {'text', 'select'}:
        error(f'{path}.input_type', '只允许text或select')
    if value.get('input_type') == 'select':
        if not isinstance(value.get('options'), list):
            error(f'{path}.options', 'select类型必须提供options数组')
        elif not value.get('options'):
            warning(f'{path}.options', '选项为空，导入后需要手动补充')


def _validate_rule(scoring_type, rule, path, error):
    if scoring_type not in SCORING_TYPES:
        return
    if not isinstance(rule, dict):
        error(path, '必须是对象')
        return
    if scoring_type == 'manual_score':
        _required_numbers(rule, ('min_score', 'max_score'), path, error)
    elif scoring_type in {'fixed_score', 'fixed_bonus'}:
        _required_numbers(rule, ('score',), path, error)
    elif scoring_type == 'tiered_score':
        _rows(rule.get('options'), ('value', 'label', 'score'), f'{path}.options', error)
    elif scoring_type == 'count_score':
        _required_numbers(rule, ('score_per_count',), path, error)
    elif scoring_type == 'count_deduction':
        _required_numbers(rule, ('initial_score', 'score_per_count'), path, error)
    elif scoring_type == 'range_score':
        _rows(rule.get('ranges'), ('score',), f'{path}.ranges', error)
    elif scoring_type == 'matrix_score':
        _rows(rule.get('scores'), ('level', 'rank', 'score'), f'{path}.scores', error)
    elif scoring_type == 'tenure_score':
        _rows(rule.get('tiers'), ('min_years', 'score'), f'{path}.tiers', error)


def _required_numbers(rule, keys, path, error):
    for key in keys:
        if not _number(rule.get(key)):
            error(f'{path}.{key}', '必须是有效数字')


def _rows(rows, keys, path, error):
    if not isinstance(rows, list) or not rows:
        error(path, '必须是非空数组')
        return
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            error(f'{path}[{index}]', '必须是对象')
            continue
        for key in keys:
            value = row.get(key)
            if key in {'score', 'min_years'} and not _number(value):
                error(f'{path}[{index}].{key}', '必须是有效数字')
            elif key not in {'score', 'min_years'} and not str(value or '').strip():
                error(f'{path}[{index}].{key}', '不能为空')


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def export_dictionary(year=None, include_ids=False):
    year = year or current_year()
    if not year:
        return None
    categories = Category.query.filter_by(academic_year_id=year.id).order_by(Category.sort_order, Category.id).all()
    result = {
        'schema_version': SCHEMA_VERSION,
        'dictionary_name': f'{year.label}校园评价字典',
        'description': '',
        'categories': [],
    }
    for category in categories:
        category_data = {
            'code': category.code, 'name': category.name, 'description': category.description,
            'order': category.sort_order, 'max_score': category.max_score, 'items': [],
        }
        if include_ids:
            category_data['id'] = category.id
        for indicator in category.indicators:
            item = indicator_to_dict(indicator, include_id=include_ids)
            category_data['items'].append(item)
        result['categories'].append(category_data)
    return result


def indicator_to_dict(indicator, include_id=True):
    data = {
        'code': indicator.code, 'name': indicator.name, 'description': indicator.description,
        'order': indicator.sort_order, 'score_group': indicator.score_group,
        'data_source': indicator.data_source, 'scoring_type': indicator.scoring_type,
        'scoring_rule': json.loads(indicator.scoring_rule_json),
        'allow_multiple_records': indicator.allow_multiple_records,
        'requires_evidence': indicator.requires_evidence, 'ai_enabled': indicator.ai_enabled,
        'secondary_tracking': json.loads(indicator.secondary_tracking_json),
        'enabled': indicator.enabled,
    }
    if include_id:
        data['id'] = indicator.id
        data['category_id'] = indicator.category_id
        data['category_name'] = indicator.category.name
    return data


def import_dictionary(data, user_id):
    validation = validate_dictionary(data)
    if not validation['valid']:
        return validation
    year = current_year()
    if not year:
        raise ValueError('请先设置当前学年')
    if EvaluationRecord.query.filter_by(academic_year_id=year.id).first():
        raise ValueError('当前学年已经产生考评数据，不能整套替换JSON字典')
    previous = export_dictionary(year)
    try:
        if previous and previous['categories']:
            db.session.add(DictionarySnapshot(
                academic_year_id=year.id,
                reason='JSON导入前自动备份',
                dictionary_json=json.dumps(previous, ensure_ascii=False),
                created_by_user_id=user_id,
            ))
        Indicator.query.filter_by(academic_year_id=year.id).delete(synchronize_session=False)
        Category.query.filter_by(academic_year_id=year.id).delete(synchronize_session=False)
        db.session.flush()
        for category_data in data['categories']:
            category = Category(
                academic_year_id=year.id, code=category_data['code'], name=category_data['name'],
                description=category_data.get('description', ''), sort_order=category_data.get('order', 0),
                max_score=category_data.get('max_score'),
            )
            db.session.add(category)
            db.session.flush()
            for item in category_data['items']:
                db.session.add(Indicator(
                    academic_year_id=year.id, category_id=category.id, code=item['code'], name=item['name'],
                    description=item.get('description', ''), sort_order=item.get('order', 0),
                    score_group=item['score_group'], data_source=item['data_source'],
                    scoring_type=item['scoring_type'],
                    scoring_rule_json=json.dumps(item['scoring_rule'], ensure_ascii=False),
                    allow_multiple_records=item['allow_multiple_records'],
                    requires_evidence=item['requires_evidence'], ai_enabled=item['ai_enabled'],
                    secondary_tracking_json=json.dumps(item['secondary_tracking'], ensure_ascii=False),
                    enabled=item['enabled'],
                ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return validation


def calculate_score(indicator, inputs):
    rule = json.loads(indicator.scoring_rule_json)
    scoring_type = indicator.scoring_type
    if scoring_type == 'manual_score':
        value = float(inputs.get('score', 0))
        return max(float(rule['min_score']), min(float(rule['max_score']), value))
    if scoring_type in {'fixed_score', 'fixed_bonus'}:
        return float(rule['score']) if inputs.get('qualified', True) else 0.0
    if scoring_type == 'tiered_score':
        selected = inputs.get('option')
        return float(next((row['score'] for row in rule['options'] if row['value'] == selected), 0))
    if scoring_type == 'count_score':
        score = float(inputs.get('count', 0)) * float(rule['score_per_count'])
        return _clamp(score, rule.get('min_score'), rule.get('max_score'))
    if scoring_type == 'count_deduction':
        deduction = float(inputs.get('count', 0)) * float(rule['score_per_count'])
        if rule.get('max_deduction') is not None:
            deduction = min(deduction, float(rule['max_deduction']))
        return _clamp(float(rule['initial_score']) - deduction, rule.get('min_score'), rule.get('max_score'))
    if scoring_type == 'range_score':
        value = float(inputs.get('value', 0))
        for row in rule['ranges']:
            lower = row.get('min') is None or value > row['min'] or (row.get('min_inclusive', True) and value == row['min'])
            upper = row.get('max') is None or value < row['max'] or (row.get('max_inclusive', False) and value == row['max'])
            if lower and upper:
                return float(row['score'])
        return 0.0
    if scoring_type == 'matrix_score':
        for row in rule['scores']:
            if row['level'] == inputs.get('level') and row['rank'] == inputs.get('rank'):
                return float(row['score'])
        return 0.0
    if scoring_type == 'tenure_score':
        years = float(inputs.get('years', 0))
        matches = [row for row in rule['tiers'] if years >= float(row['min_years'])]
        return float(matches[-1]['score']) if matches else 0.0
    return 0.0


def _clamp(value, minimum, maximum):
    if minimum is not None:
        value = max(value, float(minimum))
    if maximum is not None:
        value = min(value, float(maximum))
    return value
