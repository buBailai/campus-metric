(() => {
  const TYPE_DEFAULTS = {
    manual_score: { min_score: 0, max_score: 5 },
    fixed_score: { score: 1 },
    fixed_bonus: { score: 1 },
    tiered_score: { options: [{ value: 'excellent', label: '优秀', score: 1 }] },
    count_score: { score_per_count: 1, min_score: 0, max_score: null },
    count_deduction: { initial_score: 100, score_per_count: 1, max_deduction: null, min_score: 0, max_score: 100 },
    range_score: { ranges: [{ min: 0, max: null, min_inclusive: true, max_inclusive: false, score: 1 }] },
    matrix_score: {
      level_field: 'level', rank_field: 'rank',
      scores: [{ level: 'school', level_label: '校级', rank: 'first', rank_label: '一等奖', score: 1 }],
    },
    tenure_score: { tiers: [{ min_years: 0, score: 0 }] },
  };

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
  }[char]));
  const clone = value => JSON.parse(JSON.stringify(value));
  const isObject = value => value && typeof value === 'object' && !Array.isArray(value);
  const parseObject = value => {
    try {
      const parsed = JSON.parse(value || '{}');
      return isObject(parsed) ? parsed : null;
    } catch (_) {
      return null;
    }
  };
  const numberValue = value => value === '' ? null : Number(value);
  const disabledAttr = locked => locked ? ' disabled' : '';

  document.querySelectorAll('[data-config-editor]').forEach(editor => {
    const form = editor.closest('[data-indicator-config-form]');
    const typeSelect = form?.querySelector('[data-scoring-type]');
    const ruleFields = editor.querySelector('[data-rule-fields]');
    const trackingFields = editor.querySelector('[data-tracking-fields]');
    const ruleJson = editor.querySelector('[data-rule-json]');
    const trackingJson = editor.querySelector('[data-tracking-json]');
    const ruleStatus = editor.querySelector('[data-rule-status]');
    const trackingStatus = editor.querySelector('[data-tracking-status]');
    const locked = editor.dataset.locked === 'true';
    if (!form || !typeSelect || !ruleFields || !trackingFields || !ruleJson || !trackingJson) return;

    let rule = parseObject(ruleJson.value) || clone(TYPE_DEFAULTS[typeSelect.value] || {});
    let tracking = parseObject(trackingJson.value) || { enabled: false };

    const updateStatus = (node, valid, message) => {
      node.textContent = message;
      node.className = `json-sync-status ${valid ? 'valid' : 'invalid'}`;
    };
    const syncRuleJson = () => {
      ruleJson.value = JSON.stringify(rule, null, 2);
      updateStatus(ruleStatus, true, '✓ 已与图形控件同步');
    };
    const syncTrackingJson = () => {
      trackingJson.value = JSON.stringify(tracking, null, 2);
      updateStatus(trackingStatus, true, '✓ 已与图形控件同步');
    };

    const numberField = (label, key, value, hint = '', optional = false) => `
      <label>${esc(label)}<input type="number" step="0.1" data-rule-key="${esc(key)}" value="${value ?? ''}" placeholder="${optional ? '留空表示不限制' : ''}"${disabledAttr(locked)}>${hint ? `<small>${esc(hint)}</small>` : ''}</label>`;

    const rowField = (list, index, key, value, type = 'text', placeholder = '') => {
      if (type === 'checkbox') return `<label class="mini-check"><input type="checkbox" data-rule-list="${list}" data-row-index="${index}" data-row-key="${key}" ${value ? 'checked' : ''}${disabledAttr(locked)}><span>${esc(placeholder)}</span></label>`;
      return `<label><span>${esc(placeholder)}</span><input type="${type}" ${type === 'number' ? 'step="0.1"' : ''} data-rule-list="${list}" data-row-index="${index}" data-row-key="${key}" value="${esc(value ?? '')}"${disabledAttr(locked)}></label>`;
    };

    const rowCard = (list, index, title, body) => `
      <article class="rule-row-card"><div class="rule-row-title"><strong>${esc(title)}</strong><button type="button" data-remove-row="${list}" data-row-index="${index}"${disabledAttr(locked)}>删除</button></div><div class="rule-row-grid">${body}</div></article>`;

    const renderRows = (list, addLabel) => {
      const rows = Array.isArray(rule[list]) ? rule[list] : [];
      let cards = '';
      rows.forEach((row, index) => {
        if (list === 'options') {
          cards += rowCard(list, index, `档次 ${index + 1}`,
            rowField(list, index, 'label', row.label, 'text', '显示名称') +
            rowField(list, index, 'value', row.value, 'text', '内部编码') +
            rowField(list, index, 'score', row.score, 'number', '分数'));
        } else if (list === 'ranges') {
          cards += rowCard(list, index, `区间 ${index + 1}`,
            rowField(list, index, 'min', row.min, 'number', '最小值（可空）') +
            rowField(list, index, 'max', row.max, 'number', '最大值（可空）') +
            rowField(list, index, 'score', row.score, 'number', '对应分数') +
            `<div class="rule-check-pair">${rowField(list, index, 'min_inclusive', row.min_inclusive !== false, 'checkbox', '包含最小值')}${rowField(list, index, 'max_inclusive', !!row.max_inclusive, 'checkbox', '包含最大值')}</div>`);
        } else if (list === 'scores') {
          cards += rowCard(list, index, `查表项 ${index + 1}`,
            rowField(list, index, 'level_label', row.level_label, 'text', '级别名称') +
            rowField(list, index, 'level', row.level, 'text', '级别编码') +
            rowField(list, index, 'rank_label', row.rank_label, 'text', '奖次名称') +
            rowField(list, index, 'rank', row.rank, 'text', '奖次编码') +
            rowField(list, index, 'score', row.score, 'number', '分数'));
        } else if (list === 'tiers') {
          cards += rowCard(list, index, `年限档 ${index + 1}`,
            rowField(list, index, 'min_years', row.min_years, 'number', '至少任职年数') +
            rowField(list, index, 'score', row.score, 'number', '对应分数'));
        }
      });
      return `<div class="rule-row-list">${cards || '<div class="rule-empty-row">还没有配置项，请点击下方按钮添加。</div>'}</div><button class="config-add-button" type="button" data-add-row="${list}"${disabledAttr(locked)}>＋ ${esc(addLabel)}</button>`;
    };

    const renderExtraFields = () => {
      const fields = Array.isArray(rule.extra_fields) ? rule.extra_fields : [];
      const cards = fields.map((field, index) => {
        const optionsVisible = field.input_type === 'select';
        return `<article class="rule-row-card extra-field-card"><div class="rule-row-title"><strong>补充字段 ${index + 1}</strong><button type="button" data-remove-extra="${index}"${disabledAttr(locked)}>删除</button></div><div class="rule-row-grid extra-field-grid">
          ${rowField('extra_fields', index, 'label', field.label, 'text', '字段名称')}
          ${rowField('extra_fields', index, 'key', field.key, 'text', '字段编码')}
          <label><span>输入方式</span><select data-rule-list="extra_fields" data-row-index="${index}" data-row-key="input_type"${disabledAttr(locked)}><option value="text" ${field.input_type === 'text' || !field.input_type ? 'selected' : ''}>文本</option><option value="number" ${field.input_type === 'number' ? 'selected' : ''}>数字</option><option value="date" ${field.input_type === 'date' ? 'selected' : ''}>日期</option><option value="select" ${field.input_type === 'select' ? 'selected' : ''}>下拉选择</option></select></label>
          <label class="mini-check"><input type="checkbox" data-rule-list="extra_fields" data-row-index="${index}" data-row-key="required" ${field.required ? 'checked' : ''}${disabledAttr(locked)}><span>必填</span></label>
          ${optionsVisible ? `<label class="extra-options-input"><span>下拉选项（每行一个）</span><textarea rows="3" data-extra-options="${index}"${disabledAttr(locked)}>${esc((field.options || []).join('\n'))}</textarea></label>` : ''}
        </div></article>`;
      }).join('');
      return `<section class="extra-fields-section"><div class="sub-builder-head"><div><strong>补充填报字段</strong><small>例如学生姓名、证书编号、获奖日期</small></div><button class="config-add-button compact" type="button" data-add-extra${disabledAttr(locked)}>＋ 添加字段</button></div><div class="rule-row-list">${cards || '<div class="rule-empty-row compact">没有补充字段，可按需添加。</div>'}</div></section>`;
    };

    const renderRule = () => {
      const type = typeSelect.value;
      let html = `<div class="rule-type-intro"><strong>${esc(typeSelect.selectedOptions[0]?.textContent || type)}</strong><small>修改下方内容后，JSON 会自动更新。</small></div>`;
      if (type === 'manual_score') html += `<div class="rule-scalar-grid">${numberField('最低允许分', 'min_score', rule.min_score)}${numberField('最高允许分', 'max_score', rule.max_score)}</div>`;
      else if (type === 'fixed_score' || type === 'fixed_bonus') html += `<div class="rule-scalar-grid">${numberField('符合条件时得分', 'score', rule.score, '不符合条件时自动计 0 分')}</div>`;
      else if (type === 'tiered_score') html += renderRows('options', '添加一个评价档次');
      else if (type === 'count_score') html += `<div class="rule-scalar-grid">${numberField('每次得分', 'score_per_count', rule.score_per_count)}${numberField('最低分', 'min_score', rule.min_score, '', true)}${numberField('最高分', 'max_score', rule.max_score, '', true)}</div>`;
      else if (type === 'count_deduction') html += `<div class="rule-scalar-grid">${numberField('初始分', 'initial_score', rule.initial_score)}${numberField('每次扣分', 'score_per_count', rule.score_per_count)}${numberField('最多扣分', 'max_deduction', rule.max_deduction, '', true)}${numberField('最低分', 'min_score', rule.min_score, '', true)}${numberField('最高分', 'max_score', rule.max_score, '', true)}</div>`;
      else if (type === 'range_score') html += renderRows('ranges', '添加一个数值区间');
      else if (type === 'matrix_score') html += renderRows('scores', '添加一个级别 × 奖次组合');
      else if (type === 'tenure_score') html += renderRows('tiers', '添加一个年限档');
      html += renderExtraFields();
      ruleFields.innerHTML = html;
    };

    const renderTracking = () => {
      const enabled = !!tracking.enabled;
      const inputType = tracking.input_type || 'text';
      let html = `<label class="tracking-master-toggle"><input type="checkbox" data-track-key="enabled" ${enabled ? 'checked' : ''}${disabledAttr(locked)}><span><strong>启用二级跟踪字段</strong><small>启用后可按班级、年段等维度长期汇总</small></span></label>`;
      if (enabled) {
        html += `<div class="tracking-config-grid">
          <label>字段名称<input data-track-key="label" value="${esc(tracking.label || '')}" placeholder="例如：班级"${disabledAttr(locked)}></label>
          <label>输入方式<select data-track-key="input_type"${disabledAttr(locked)}><option value="text" ${inputType === 'text' ? 'selected' : ''}>自由填写</option><option value="select" ${inputType === 'select' ? 'selected' : ''}>下拉选择</option></select></label>
          <label class="mini-check required-track"><input type="checkbox" data-track-key="required" ${tracking.required ? 'checked' : ''}${disabledAttr(locked)}><span>设为必填</span></label>
        </div>`;
        if (inputType === 'select') {
          const options = Array.isArray(tracking.options) ? tracking.options : [];
          html += `<div class="tracking-options"><div class="sub-builder-head"><div><strong>下拉选项</strong><small>教师填报时只能从这些值中选择</small></div><button class="config-add-button compact" type="button" data-add-track-option${disabledAttr(locked)}>＋ 添加选项</button></div><div class="tracking-option-list">${options.map((option, index) => `<div><input value="${esc(option)}" data-track-option-index="${index}" placeholder="例如：三年1班"${disabledAttr(locked)}><button type="button" data-remove-track-option="${index}"${disabledAttr(locked)}>删除</button></div>`).join('') || '<div class="rule-empty-row compact">暂无选项，请先添加。</div>'}</div></div>`;
        }
      }
      trackingFields.innerHTML = html;
    };

    const addRow = list => {
      if (!Array.isArray(rule[list])) rule[list] = [];
      const defaults = {
        options: { value: `option_${rule[list].length + 1}`, label: '新档次', score: 0 },
        ranges: { min: 0, max: null, min_inclusive: true, max_inclusive: false, score: 0 },
        scores: { level: 'school', level_label: '校级', rank: `rank_${rule[list].length + 1}`, rank_label: '新奖次', score: 0 },
        tiers: { min_years: 0, score: 0 },
      };
      rule[list].push(defaults[list]);
      syncRuleJson();
      renderRule();
    };

    typeSelect.addEventListener('change', () => {
      if (locked) return;
      const extras = Array.isArray(rule.extra_fields) ? clone(rule.extra_fields) : [];
      rule = clone(TYPE_DEFAULTS[typeSelect.value] || {});
      if (extras.length) rule.extra_fields = extras;
      syncRuleJson();
      renderRule();
    });

    ruleFields.addEventListener('click', event => {
      if (locked) return;
      const add = event.target.closest('[data-add-row]');
      const remove = event.target.closest('[data-remove-row]');
      const addExtra = event.target.closest('[data-add-extra]');
      const removeExtra = event.target.closest('[data-remove-extra]');
      if (add) addRow(add.dataset.addRow);
      else if (remove) {
        rule[remove.dataset.removeRow]?.splice(Number(remove.dataset.rowIndex), 1);
        syncRuleJson(); renderRule();
      } else if (addExtra) {
        if (!Array.isArray(rule.extra_fields)) rule.extra_fields = [];
        rule.extra_fields.push({ key: `field_${rule.extra_fields.length + 1}`, label: '补充字段', input_type: 'text', required: false });
        syncRuleJson(); renderRule();
      } else if (removeExtra) {
        rule.extra_fields?.splice(Number(removeExtra.dataset.removeExtra), 1);
        if (!rule.extra_fields?.length) delete rule.extra_fields;
        syncRuleJson(); renderRule();
      }
    });

    const handleRuleControl = event => {
      if (locked) return;
      const control = event.target;
      if (control.dataset.ruleKey) {
        rule[control.dataset.ruleKey] = numberValue(control.value);
      } else if (control.dataset.ruleList) {
        const row = rule[control.dataset.ruleList]?.[Number(control.dataset.rowIndex)];
        if (!row) return;
        let value = control.type === 'checkbox' ? control.checked : control.type === 'number' ? numberValue(control.value) : control.value;
        row[control.dataset.rowKey] = value;
        if (control.dataset.rowKey === 'input_type') {
          if (value === 'select' && !Array.isArray(row.options)) row.options = [];
          renderRule();
        }
      } else if (control.dataset.extraOptions !== undefined) {
        const row = rule.extra_fields?.[Number(control.dataset.extraOptions)];
        if (row) row.options = control.value.split(/[\n,，、;；]+/).map(item => item.trim()).filter(Boolean);
      }
      syncRuleJson();
    };
    ruleFields.addEventListener('input', handleRuleControl);
    ruleFields.addEventListener('change', handleRuleControl);

    trackingFields.addEventListener('click', event => {
      if (locked) return;
      if (event.target.closest('[data-add-track-option]')) {
        if (!Array.isArray(tracking.options)) tracking.options = [];
        tracking.options.push(`选项${tracking.options.length + 1}`);
        syncTrackingJson(); renderTracking();
      }
      const remove = event.target.closest('[data-remove-track-option]');
      if (remove) {
        tracking.options?.splice(Number(remove.dataset.removeTrackOption), 1);
        syncTrackingJson(); renderTracking();
      }
    });

    const handleTrackingControl = event => {
      if (locked) return;
      const control = event.target;
      if (control.dataset.trackKey) {
        tracking[control.dataset.trackKey] = control.type === 'checkbox' ? control.checked : control.value;
        if (control.dataset.trackKey === 'enabled' || control.dataset.trackKey === 'input_type') {
          if (tracking.enabled) {
            tracking.label ||= '班级';
            tracking.input_type ||= 'text';
            if (tracking.input_type === 'select' && !Array.isArray(tracking.options)) tracking.options = [];
          }
          renderTracking();
        }
      } else if (control.dataset.trackOptionIndex !== undefined) {
        tracking.options[Number(control.dataset.trackOptionIndex)] = control.value;
      }
      syncTrackingJson();
    };
    trackingFields.addEventListener('input', handleTrackingControl);
    trackingFields.addEventListener('change', handleTrackingControl);

    const bindJsonEditor = (textarea, status, kind) => {
      const apply = () => {
        const parsed = parseObject(textarea.value);
        if (!parsed) {
          updateStatus(status, false, 'JSON 格式不完整，修正后才能保存');
          return false;
        }
        if (kind === 'rule') { rule = parsed; renderRule(); }
        else { tracking = parsed; renderTracking(); }
        updateStatus(status, true, '✓ JSON 已反向同步到图形控件');
        return true;
      };
      textarea.addEventListener('input', apply);
      textarea.addEventListener('blur', apply);
      return apply;
    };
    const applyRuleJson = bindJsonEditor(ruleJson, ruleStatus, 'rule');
    const applyTrackingJson = bindJsonEditor(trackingJson, trackingStatus, 'tracking');

    form.addEventListener('submit', event => {
      if (locked) return;
      const ruleValid = applyRuleJson();
      const trackingValid = applyTrackingJson();
      if (ruleValid && trackingValid) return;
      event.preventDefault();
      if (!ruleValid) editor.querySelector('[data-rule-advanced]').open = true;
      if (!trackingValid) editor.querySelector('[data-tracking-advanced]').open = true;
      window.showToast?.('JSON 格式有误，请修正红色提示后再保存。', 'danger');
    });

    syncRuleJson();
    syncTrackingJson();
    renderRule();
    renderTracking();
  });
})();
