(() => {
  const shell = document.querySelector('[data-entry-mode]');
  if (!shell) return;
  const mode = shell.dataset.entryMode;
  const editRecordId = Number(shell.dataset.editRecordId || 0);
  const list = document.getElementById('indicator-list');
  const search = document.getElementById('indicator-search');
  const form = document.getElementById('dynamic-entry-form');
  const empty = document.getElementById('form-empty');
  const fields = document.getElementById('dynamic-fields');
  const trackingWrapper = document.getElementById('tracking-wrapper');
  const trackingControl = document.getElementById('tracking-control');
  const evidenceWrapper = document.getElementById('evidence-wrapper');
  const evidenceFiles = document.getElementById('evidence-files');
  const aiRecognitionBox = document.getElementById('ai-recognition-box');
  const aiRecognizeButton = document.getElementById('ai-recognize-entry');
  const aiRecognitionResult = document.getElementById('ai-recognition-result');
  const noteInput = document.getElementById('entry-note');
  const preview = document.getElementById('score-preview');
  const targetUser = document.getElementById('target-user');
  const existingAttachmentBox = document.getElementById('existing-attachment');
  let categories = [];
  let selected = null;
  let existingAttachment = null;

  const batchPanel = document.getElementById('batch-panel');
  const singlePanel = form ? form.closest('.dynamic-form-panel') : null;
  const modeSingleBtn = document.getElementById('mode-single');
  const modeBatchBtn = document.getElementById('mode-batch');
  let batchMode = false;

  loadIndicators();

  async function loadIndicators() {
    try {
      const response = await fetch(window.appUrl(`/api/entry-indicators?mode=${mode === 'admin' ? 'admin' : 'teacher'}`));
      const data = await response.json();
      categories = data.categories || [];
      renderList('');
      if (editRecordId) await loadEditRecord();
    } catch (error) {
      list.innerHTML = `<div class="empty-state"><h3>读取失败</h3><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  search.addEventListener('input', () => renderList(search.value.trim().toLowerCase()));

  function renderList(keyword) {
    const blocks = categories.map(category => {
      const indicators = category.indicators.filter(item => !keyword || `${item.name} ${item.code} ${item.description}`.toLowerCase().includes(keyword));
      if (!indicators.length) return '';
      return `<section class="picker-category"><h3>${escapeHtml(category.name)}</h3>${indicators.map(item => `
        <button type="button" class="picker-button" data-id="${item.id}"><strong>${escapeHtml(item.name)}</strong><small>${labelForType(item.scoring_type)} · ${item.requires_evidence ? '需材料' : '无需材料'}</small></button>
      `).join('')}</section>`;
    }).join('');
    list.innerHTML = blocks || '<div class="empty-state"><h3>没有可录入指标</h3><p>请先在管理端配置对应数据来源的指标。</p></div>';
    list.querySelectorAll('[data-id]').forEach(button => button.addEventListener('click', () => selectIndicator(Number(button.dataset.id), button)));
  }

  function selectIndicator(id, button, initial = null) {
    selected = categories.flatMap(category => category.indicators.map(indicator => ({ ...indicator, category_name: category.name }))).find(item => item.id === id);
    if (!selected) return;
    list.querySelectorAll('.picker-button').forEach(node => node.classList.toggle('active', node === button));
    if (batchMode) { renderBatchIndicator(); return; }
    empty.hidden = true;
    form.hidden = false;
    document.getElementById('selected-category').textContent = selected.category_name;
    document.getElementById('selected-name').textContent = selected.name;
    document.getElementById('selected-description').textContent = selected.description || '按当前考评字典规则录入。';
    fields.innerHTML = fieldHtml(selected);
    renderTracking(selected.secondary_tracking || { enabled: false });
    evidenceWrapper.hidden = !selected.requires_evidence;
    existingAttachment = initial?.attachment || null;
    evidenceFiles.required = Boolean(selected.requires_evidence && !existingAttachment);
    evidenceFiles.value = '';
    existingAttachmentBox.hidden = !existingAttachment;
    existingAttachmentBox.textContent = existingAttachment ? `当前材料：${existingAttachment.name}；如需替换，请重新选择一张图片。` : '';
    aiRecognitionBox.hidden = !selected.ai_enabled;
    aiRecognizeButton.disabled = true;
    aiRecognitionResult.hidden = true;
    aiRecognitionResult.textContent = '';
    noteInput.value = initial?.note || '';
    form.querySelectorAll('input, select').forEach(control => control.addEventListener('input', updatePreview));
    applyTargetDefaults();
    if (initial) {
      Object.entries(initial.inputs || {}).forEach(([key, value]) => {
        const control = form.querySelector(`[data-input="${key}"]`);
        if (control && value !== null && value !== undefined) control.value = String(value);
      });
      const tracking = document.getElementById('tracking-value');
      if (tracking) tracking.value = initial.secondary_tracking_value || '';
      list.querySelectorAll('.picker-button').forEach(node => { node.disabled = Number(node.dataset.id) !== id; });
    }
    updatePreview();
  }

  async function loadEditRecord() {
    try {
      const response = await fetch(window.appUrl(`/api/records/${editRecordId}`));
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || '待审核记录读取失败');
      const button = list.querySelector(`[data-id="${data.indicator_id}"]`);
      if (!button) throw new Error('原考评指标已停用，暂时无法编辑');
      selectIndicator(Number(data.indicator_id), button, data);
      button.scrollIntoView({ block: 'nearest' });
    } catch (error) {
      showToast(error.message, 'danger');
    }
  }

  if (targetUser) targetUser.addEventListener('change', () => { applyTargetDefaults(); updatePreview(); });
  evidenceFiles.addEventListener('change', () => {
    aiRecognizeButton.disabled = !selected?.ai_enabled || evidenceFiles.files.length !== 1;
    aiRecognitionResult.hidden = true;
  });

  aiRecognizeButton.addEventListener('click', recognizeAndFill);

  async function recognizeAndFill() {
    if (!selected?.ai_enabled || evidenceFiles.files.length !== 1) {
      showToast('请先选择一张证书或材料图片', 'danger');
      return;
    }
    const body = new FormData();
    body.append('indicator_id', selected.id);
    body.append('file', evidenceFiles.files[0]);
    aiRecognizeButton.disabled = true;
    aiRecognizeButton.textContent = '正在识别并匹配当前表单…';
    aiRecognitionResult.hidden = false;
    aiRecognitionResult.className = 'validation-result';
    aiRecognitionResult.textContent = '正在读取图片中的证书名称、人员、级别、奖次、单位和日期…';
    try {
      const response = await fetch(window.appUrl('/api/entry/recognize'), { method: 'POST', body });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || 'AI 识别失败');
      Object.entries(data.inputs || {}).forEach(([key, value]) => {
        const control = form.querySelector(`[data-input="${key}"]`);
        if (control && value !== null && value !== undefined) control.value = String(value);
      });
      const tracking = document.getElementById('tracking-value');
      if (tracking && data.secondary_tracking_value) tracking.value = data.secondary_tracking_value;
      const aiNote = `[AI识别] ${data.note || ''}`.trim();
      if (!noteInput.value.trim() || noteInput.value.startsWith('[AI识别]')) noteInput.value = aiNote;
      else noteInput.value = `${noteInput.value.trim()}\n${aiNote}`;
      updatePreview();
      aiRecognitionResult.className = 'validation-result valid';
      aiRecognitionResult.textContent = `${data.message}\n请对照原图核对后再提交。`;
      showToast(data.message);
    } catch (error) {
      aiRecognitionResult.className = 'validation-result invalid';
      aiRecognitionResult.textContent = `${error.message}\n你仍可直接手动填写并提交。`;
      showToast(error.message, 'danger');
    } finally {
      aiRecognizeButton.disabled = evidenceFiles.files.length !== 1;
      aiRecognizeButton.textContent = '✦ AI 识别并自动填写';
    }
  }

  function applyTargetDefaults() {
    if (!targetUser || !selected) return;
    const option = targetUser.selectedOptions[0];
    if (!option) return;
    if (selected.scoring_type === 'tenure_score') {
      const years = form.querySelector('[data-input="years"]');
      if (years) years.value = option.dataset.tenure || 0;
    }
    if (selected.scoring_type === 'fixed_bonus' && selected.name.includes('年段长')) {
      const qualified = form.querySelector('[data-input="qualified"]');
      if (qualified) qualified.value = option.dataset.gradeLeader === '1' ? 'true' : 'false';
    }
  }

  function fieldHtml(item) {
    return scoringFieldHtml(item) + extraFieldsHtml((item.scoring_rule || {}).extra_fields || []);
  }

  function scoringFieldHtml(item) {
    const rule = item.scoring_rule || {};
    switch (item.scoring_type) {
      case 'manual_score':
        return `<label>实际得分<input data-input="score" type="number" step="0.1" min="${rule.min_score}" max="${rule.max_score}" required><small>允许范围：${rule.min_score}—${rule.max_score} 分</small></label>`;
      case 'fixed_score':
      case 'fixed_bonus':
        return `<label>是否符合条件<select data-input="qualified"><option value="true">符合，计 ${rule.score} 分</option><option value="false">不符合，计 0 分</option></select></label>`;
      case 'tiered_score':
        return `<label>评价档次<select data-input="option" required><option value="">请选择</option>${(rule.options || []).map(row => `<option value="${escapeAttr(row.value)}">${escapeHtml(row.label)} · ${row.score} 分</option>`).join('')}</select></label>`;
      case 'count_score':
        if (item.requires_evidence) return `<label>本条材料数量<input data-input="count" type="number" value="1" readonly><small>需要材料的项目固定一条一份，更多材料请再次新增。</small></label>`;
      case 'count_deduction':
        return `<label>次数<input data-input="count" type="number" min="0" step="1" value="0" required></label>`;
      case 'range_score':
        return `<label>统计数值<input data-input="value" type="number" step="0.1" required placeholder="填写满意率、平台分数等"></label>`;
      case 'matrix_score': {
        const levels = unique((rule.scores || []).map(row => ({ value: row.level, label: row.level_label || row.level })));
        const ranks = unique((rule.scores || []).map(row => ({ value: row.rank, label: row.rank_label || row.rank })));
        return `<div class="inline-options"><label>获奖级别<select data-input="level" required><option value="">请选择</option>${options(levels)}</select></label><label>奖次<select data-input="rank" required><option value="">请选择</option>${options(ranks)}</select></label></div>`;
      }
      case 'tenure_score':
        return `<label>班主任任职年限<input data-input="years" type="number" min="0" step="1" required></label>`;
      default:
        return '<p>该积分类型暂不支持动态录入。</p>';
    }
  }

  function extraFieldsHtml(extraFields) {
    return extraFields.map(field => {
      const key = escapeAttr(field.key || '');
      const label = escapeHtml(field.label || field.key || '补充字段');
      const required = field.required ? 'required' : '';
      if (field.input_type === 'select') {
        return `<label>${label}<select data-input="${key}" ${required}><option value="">请选择</option>${(field.options || []).map(value => `<option value="${escapeAttr(value)}">${escapeHtml(value)}</option>`).join('')}</select></label>`;
      }
      const type = ['text', 'date', 'number'].includes(field.input_type) ? field.input_type : 'text';
      return `<label>${label}<input data-input="${key}" type="${type}" ${required}></label>`;
    }).join('');
  }

  function renderTracking(config) {
    trackingControl.innerHTML = '';
    trackingWrapper.hidden = !config.enabled;
    if (!config.enabled) return;
    document.getElementById('tracking-label').textContent = config.label || '补充字段';
    if (config.input_type === 'select') {
      trackingControl.innerHTML = `<select id="tracking-value" ${config.required ? 'required' : ''}><option value="">请选择</option>${(config.options || []).map(value => `<option value="${escapeAttr(value)}">${escapeHtml(value)}</option>`).join('')}</select>`;
    } else {
      trackingControl.innerHTML = `<input id="tracking-value" ${config.required ? 'required' : ''}>`;
    }
  }

  function collectInputs() {
    const result = {};
    form.querySelectorAll('[data-input]').forEach(control => {
      let value = control.value;
      if (['score', 'count', 'value', 'years'].includes(control.dataset.input)) value = value === '' ? null : Number(value);
      if (control.dataset.input === 'qualified') value = value === 'true';
      result[control.dataset.input] = value;
    });
    return result;
  }

  function compute(item, input) {
    const rule = item.scoring_rule || {};
    if (item.scoring_type === 'manual_score') return clamp(input.score || 0, rule.min_score, rule.max_score);
    if (['fixed_score', 'fixed_bonus'].includes(item.scoring_type)) return input.qualified === false ? 0 : Number(rule.score || 0);
    if (item.scoring_type === 'tiered_score') return Number((rule.options || []).find(row => row.value === input.option)?.score || 0);
    if (item.scoring_type === 'count_score') return clamp(Number(input.count || 0) * Number(rule.score_per_count || 0), rule.min_score, rule.max_score);
    if (item.scoring_type === 'count_deduction') {
      const deduction = Math.min(Number(input.count || 0) * Number(rule.score_per_count || 0), rule.max_deduction ?? Infinity);
      return clamp(Number(rule.initial_score || 0) - deduction, rule.min_score, rule.max_score);
    }
    if (item.scoring_type === 'range_score') {
      const value = Number(input.value);
      const row = (rule.ranges || []).find(r => (r.min == null || value > r.min || (r.min_inclusive !== false && value === r.min)) && (r.max == null || value < r.max || (r.max_inclusive === true && value === r.max)));
      return Number(row?.score || 0);
    }
    if (item.scoring_type === 'matrix_score') return Number((rule.scores || []).find(row => row.level === input.level && row.rank === input.rank)?.score || 0);
    if (item.scoring_type === 'tenure_score') {
      const rows = (rule.tiers || []).filter(row => Number(input.years || 0) >= row.min_years);
      return Number(rows.at(-1)?.score || 0);
    }
    return 0;
  }

  function updatePreview() {
    if (!selected) return;
    preview.textContent = `${formatScore(compute(selected, collectInputs()))} 分`;
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!selected || !form.reportValidity()) return;
    const target = document.getElementById('target-user');
    const payload = {
      indicator_id: selected.id,
      target_user_id: target ? Number(target.value) : undefined,
      inputs: collectInputs(),
      secondary_tracking_value: document.getElementById('tracking-value')?.value || '',
      note: document.getElementById('entry-note').value,
    };
    const submit = form.querySelector('[type="submit"]');
    const files = [...evidenceFiles.files];
    submit.disabled = true;
    try {
      const saveUrl = editRecordId ? `/api/records/${editRecordId}` : '/api/records';
      const response = await fetch(window.appUrl(saveUrl), { method: editRecordId ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || '保存失败');
      let attachmentResult = null;
      if (files.length) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        if (editRecordId && existingAttachment) formData.append('replace', 'true');
        const uploadResponse = await fetch(window.appUrl(`/api/records/${result.record_id}/attachments`), { method: 'POST', body: formData });
        attachmentResult = await uploadResponse.json();
        if (!uploadResponse.ok || !attachmentResult.ok) throw new Error(attachmentResult.message || '图片上传失败');
      }
      showToast(`${result.message} · ${formatScore(result.auto_score)} 分`);
      if (editRecordId) {
        window.setTimeout(() => { window.location.href = window.appUrl('/my/results'); }, 500);
        return;
      }
      form.reset();
      aiRecognizeButton.disabled = true;
      aiRecognitionResult.hidden = true;
      updatePreview();
    } catch (error) {
      showToast(error.message, 'danger');
    } finally {
      submit.disabled = false;
    }
  });

  // ===== 批量录入（仅管理员，多选教师 → 表格逐行录入 → 暂存/一次性提交；每行仍走原单条 /api/records 数据格式） =====
  const batchForm = document.getElementById('batch-form');
  const batchEmpty = document.getElementById('batch-empty');
  const batchTeacherList = document.getElementById('batch-teacher-list');
  const batchTable = document.getElementById('batch-table');
  const batchTableWrap = document.getElementById('batch-table-wrap');
  const batchActions = document.getElementById('batch-actions');
  const batchEvidenceNote = document.getElementById('batch-evidence-note');
  const batchPicker = document.getElementById('batch-picker');
  const batchDraftHint = document.getElementById('batch-draft-hint');
  const batchCount = document.getElementById('batch-count');

  if (modeSingleBtn && modeBatchBtn && batchPanel) {
    modeSingleBtn.addEventListener('click', () => setBatchMode(false));
    modeBatchBtn.addEventListener('click', () => setBatchMode(true));
    document.getElementById('batch-teacher-search').addEventListener('input', event => {
      const keyword = event.target.value.trim();
      batchTeacherList.querySelectorAll('.batch-teacher-item').forEach(item => {
        item.hidden = Boolean(keyword) && !item.textContent.includes(keyword);
      });
    });
    document.getElementById('batch-select-all').addEventListener('click', () => {
      batchTeacherList.querySelectorAll('.batch-teacher-item:not([hidden]) input').forEach(box => { box.checked = true; });
      renderBatchTable(true);
    });
    document.getElementById('batch-clear-all').addEventListener('click', () => {
      batchTeacherList.querySelectorAll('input:checked').forEach(box => { box.checked = false; });
      renderBatchTable(true);
    });
    batchTeacherList.addEventListener('change', () => renderBatchTable(true));
    batchTable.addEventListener('input', event => {
      const row = event.target.closest('tr[data-teacher]');
      if (row) updateRowPreview(row);
    });
    document.getElementById('batch-fill-down').addEventListener('click', fillDownFirstRow);
    document.getElementById('batch-save-draft').addEventListener('click', () => saveBatchDraft(true));
    batchForm.addEventListener('submit', submitBatch);
  }

  function setBatchMode(next) {
    if (batchMode === next) return;
    batchMode = next;
    modeSingleBtn.classList.toggle('active', !next);
    modeBatchBtn.classList.toggle('active', next);
    singlePanel.hidden = next;
    batchPanel.hidden = !next;
    const activeButton = list.querySelector('.picker-button.active');
    if (next) {
      if (selected) renderBatchIndicator();
    } else if (selected && activeButton) {
      selectIndicator(selected.id, activeButton);
    }
  }

  function renderBatchIndicator() {
    batchEmpty.hidden = true;
    batchForm.hidden = false;
    document.getElementById('batch-category').textContent = selected.category_name;
    document.getElementById('batch-name').textContent = selected.name;
    document.getElementById('batch-description').textContent = selected.description || '按当前考评字典规则录入。';
    batchEvidenceNote.hidden = !selected.requires_evidence;
    batchPicker.hidden = false;
    batchDraftHint.textContent = '';
    const draft = loadBatchDraft();
    if (draft) {
      batchTeacherList.querySelectorAll('input[type="checkbox"]').forEach(box => { box.checked = draft.teachers.includes(Number(box.value)); });
    }
    renderBatchTable(false, draft ? draft.rows : null);
    if (draft) {
      batchDraftHint.textContent = `已恢复 ${draft.saved_at} 的暂存`;
      showToast('已恢复上次暂存的批量录入内容');
    }
  }

  function batchColumnSpecs(item) {
    const rule = item.scoring_rule || {};
    const specs = [];
    switch (item.scoring_type) {
      case 'manual_score':
        specs.push({ label: `实际得分（${rule.min_score}—${rule.max_score}）`, html: () => `<input data-input="score" type="number" step="0.1" min="${rule.min_score}" max="${rule.max_score}" required>` });
        break;
      case 'fixed_score':
      case 'fixed_bonus':
        specs.push({ label: '是否符合条件', html: teacher => {
          const preset = item.scoring_type === 'fixed_bonus' && item.name.includes('年段长') ? teacher.gradeLeader : true;
          return `<select data-input="qualified"><option value="true" ${preset ? 'selected' : ''}>符合，计 ${rule.score} 分</option><option value="false" ${preset ? '' : 'selected'}>不符合，计 0 分</option></select>`;
        } });
        break;
      case 'tiered_score':
        specs.push({ label: '评价档次', html: () => `<select data-input="option" required><option value="">请选择</option>${(rule.options || []).map(row => `<option value="${escapeAttr(row.value)}">${escapeHtml(row.label)} · ${row.score} 分</option>`).join('')}</select>` });
        break;
      case 'count_score':
        if (item.requires_evidence) {
          specs.push({ label: '本条材料数量', html: () => `<input data-input="count" type="number" value="1" readonly>` });
          break;
        }
      case 'count_deduction':
        specs.push({ label: '次数', html: () => `<input data-input="count" type="number" min="0" step="1" value="0" required>` });
        break;
      case 'range_score':
        specs.push({ label: '统计数值', html: () => `<input data-input="value" type="number" step="0.1" required placeholder="满意率、平台分数等">` });
        break;
      case 'matrix_score': {
        const levels = unique((rule.scores || []).map(row => ({ value: row.level, label: row.level_label || row.level })));
        const ranks = unique((rule.scores || []).map(row => ({ value: row.rank, label: row.rank_label || row.rank })));
        specs.push({ label: '获奖级别', html: () => `<select data-input="level" required><option value="">请选择</option>${options(levels)}</select>` });
        specs.push({ label: '奖次', html: () => `<select data-input="rank" required><option value="">请选择</option>${options(ranks)}</select>` });
        break;
      }
      case 'tenure_score':
        specs.push({ label: '任职年限', html: teacher => `<input data-input="years" type="number" min="0" step="1" value="${teacher.tenure}" required>` });
        break;
      default:
        break;
    }
    ((item.scoring_rule || {}).extra_fields || []).forEach(field => {
      const key = escapeAttr(field.key || '');
      const required = field.required ? 'required' : '';
      if (field.input_type === 'select') {
        specs.push({ label: field.label || field.key || '补充字段', html: () => `<select data-input="${key}" ${required}><option value="">请选择</option>${(field.options || []).map(value => `<option value="${escapeAttr(value)}">${escapeHtml(value)}</option>`).join('')}</select>` });
      } else {
        const type = ['text', 'date', 'number'].includes(field.input_type) ? field.input_type : 'text';
        specs.push({ label: field.label || field.key || '补充字段', html: () => `<input data-input="${key}" type="${type}" ${required}>` });
      }
    });
    const tracking = item.secondary_tracking || { enabled: false };
    if (tracking.enabled) {
      if (tracking.input_type === 'select') {
        specs.push({ label: tracking.label || '补充字段', html: () => `<select data-batch-tracking ${tracking.required ? 'required' : ''}><option value="">请选择</option>${(tracking.options || []).map(value => `<option value="${escapeAttr(value)}">${escapeHtml(value)}</option>`).join('')}</select>` });
      } else {
        specs.push({ label: tracking.label || '补充字段', html: () => `<input data-batch-tracking ${tracking.required ? 'required' : ''}>` });
      }
    }
    if (item.requires_evidence) {
      specs.push({ label: '材料图片（1 张）', html: () => `<input data-batch-file type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" required>` });
    }
    specs.push({ label: '补充说明', html: () => `<input data-batch-note placeholder="可选">` });
    return specs;
  }

  function checkedTeachers() {
    return [...batchTeacherList.querySelectorAll('input:checked')].map(box => ({
      id: Number(box.value),
      name: box.dataset.name,
      tenure: Number(box.dataset.tenure || 0),
      gradeLeader: box.dataset.gradeLeader === '1',
    }));
  }

  function snapshotRows() {
    const rows = {};
    batchTable.querySelectorAll('tr[data-teacher]').forEach(row => { rows[row.dataset.teacher] = collectRowValues(row); });
    return rows;
  }

  function collectRowValues(row) {
    const values = { inputs: {}, tracking: '', note: '' };
    row.querySelectorAll('[data-input]').forEach(control => { values.inputs[control.dataset.input] = control.value; });
    const tracking = row.querySelector('[data-batch-tracking]');
    if (tracking) values.tracking = tracking.value;
    const note = row.querySelector('[data-batch-note]');
    if (note) values.note = note.value;
    return values;
  }

  function applyRowValues(row, values) {
    if (!values) return;
    Object.entries(values.inputs || {}).forEach(([key, value]) => {
      const control = row.querySelector(`[data-input="${key}"]`);
      if (control && value !== '' && value !== null && value !== undefined) control.value = String(value);
    });
    const tracking = row.querySelector('[data-batch-tracking]');
    if (tracking && values.tracking) tracking.value = values.tracking;
    const note = row.querySelector('[data-batch-note]');
    if (note && values.note) note.value = values.note;
  }

  function renderBatchTable(preserve, draftRows = null) {
    if (!selected || batchMode === false) return;
    const previous = preserve ? snapshotRows() : {};
    const teachers = checkedTeachers();
    batchCount.textContent = `已选 ${teachers.length} 人`;
    batchTableWrap.hidden = !teachers.length;
    batchActions.hidden = !teachers.length;
    if (!teachers.length) { batchTable.innerHTML = ''; return; }
    const specs = batchColumnSpecs(selected);
    batchTable.innerHTML = `<thead><tr><th>教师</th>${specs.map(spec => `<th>${escapeHtml(spec.label)}</th>`).join('')}<th>预计得分</th><th>状态</th></tr></thead><tbody>${teachers.map(teacher => `
      <tr data-teacher="${teacher.id}"><td class="batch-name-cell">${escapeHtml(teacher.name)}</td>${specs.map(spec => `<td>${spec.html(teacher)}</td>`).join('')}<td class="batch-score">—</td><td class="batch-status"></td></tr>`).join('')}</tbody>`;
    batchTable.querySelectorAll('tr[data-teacher]').forEach(row => {
      applyRowValues(row, (draftRows || previous)[row.dataset.teacher]);
      updateRowPreview(row);
    });
    document.getElementById('batch-submit').textContent = `一次性提交 ${teachers.length} 条`;
  }

  function rowInputs(row) {
    const result = {};
    row.querySelectorAll('[data-input]').forEach(control => {
      let value = control.value;
      if (['score', 'count', 'value', 'years'].includes(control.dataset.input)) value = value === '' ? null : Number(value);
      if (control.dataset.input === 'qualified') value = value === 'true';
      result[control.dataset.input] = value;
    });
    return result;
  }

  function updateRowPreview(row) {
    row.querySelector('.batch-score').textContent = `${formatScore(compute(selected, rowInputs(row)))} 分`;
  }

  function fillDownFirstRow() {
    const rows = [...batchTable.querySelectorAll('tr[data-teacher]:not([data-done])')];
    if (rows.length < 2) return;
    const source = collectRowValues(rows[0]);
    rows.slice(1).forEach(row => { applyRowValues(row, source); updateRowPreview(row); });
    showToast('已将首行内容填充到其余行，请逐行核对。');
  }

  function draftKey() { return `ce-batch-draft:${selected.id}`; }

  function saveBatchDraft(announce) {
    if (!selected) return;
    const teachers = checkedTeachers().map(teacher => teacher.id);
    const stamp = new Date().toLocaleString('zh-CN', { hour12: false });
    try {
      localStorage.setItem(draftKey(), JSON.stringify({ teachers, rows: snapshotRows(), saved_at: stamp }));
      batchDraftHint.textContent = `已暂存 · ${stamp}`;
      if (announce) showToast(selected.requires_evidence ? '已暂存（图片不会保存，恢复后需重新选择）。' : '已暂存到本浏览器，下次打开该指标的批量录入会自动恢复。');
    } catch (error) {
      showToast('暂存失败：浏览器存储不可用', 'danger');
    }
  }

  function loadBatchDraft() {
    try {
      const raw = localStorage.getItem(draftKey());
      if (!raw) return null;
      const draft = JSON.parse(raw);
      if (!Array.isArray(draft.teachers) || !draft.teachers.length) return null;
      return draft;
    } catch (error) { return null; }
  }

  async function submitBatch(event) {
    event.preventDefault();
    const rows = [...batchTable.querySelectorAll('tr[data-teacher]:not([data-done])')];
    if (!selected || !rows.length) { showToast('没有待提交的行', 'danger'); return; }
    if (!batchForm.reportValidity()) return;
    const submit = document.getElementById('batch-submit');
    submit.disabled = true;
    let succeeded = 0; let failed = 0;
    for (const row of rows) {
      const status = row.querySelector('.batch-status');
      status.textContent = '提交中…';
      status.className = 'batch-status';
      const payload = {
        indicator_id: selected.id,
        target_user_id: Number(row.dataset.teacher),
        inputs: rowInputs(row),
        secondary_tracking_value: row.querySelector('[data-batch-tracking]')?.value || '',
        note: row.querySelector('[data-batch-note]')?.value || '',
      };
      const fileInput = row.querySelector('[data-batch-file]');
      try {
        const response = await fetch(window.appUrl('/api/records'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.message || '保存失败');
        row.dataset.done = '1';
        if (fileInput && fileInput.files.length) {
          status.textContent = '上传图片中…';
          const formData = new FormData();
          formData.append('files', fileInput.files[0]);
          const uploadResponse = await fetch(window.appUrl(`/api/records/${result.record_id}/attachments`), { method: 'POST', body: formData });
          const uploadResult = await uploadResponse.json();
          if (!uploadResponse.ok || !uploadResult.ok) {
            row.querySelectorAll('input, select').forEach(control => { control.disabled = true; });
            status.textContent = `⚠ 已计 ${formatScore(result.auto_score)} 分，但图片上传失败：${uploadResult.message || '未知错误'}。请到考评记录中补传。`;
            status.classList.add('fail');
            failed += 1;
            continue;
          }
        }
        row.querySelectorAll('input, select').forEach(control => { control.disabled = true; });
        status.textContent = `✓ 已计 ${formatScore(result.auto_score)} 分`;
        status.classList.add('ok');
        succeeded += 1;
      } catch (error) {
        status.textContent = `✗ ${error.message}`;
        status.classList.add('fail');
        failed += 1;
      }
    }
    submit.disabled = false;
    const remaining = batchTable.querySelectorAll('tr[data-teacher]:not([data-done])').length;
    document.getElementById('batch-submit').textContent = remaining ? `重新提交剩余 ${remaining} 条` : '全部已提交';
    if (!remaining) { try { localStorage.removeItem(draftKey()); } catch (error) { /* 忽略 */ } batchDraftHint.textContent = ''; }
    showToast(failed ? `成功 ${succeeded} 条，失败 ${failed} 条，失败行可修改后重新提交。` : `已全部提交，共 ${succeeded} 条。`, failed ? 'danger' : 'success');
  }

  function unique(rows) { return [...new Map(rows.map(row => [row.value, row])).values()]; }
  function options(rows) { return rows.map(row => `<option value="${escapeAttr(row.value)}">${escapeHtml(row.label)}</option>`).join(''); }
  function clamp(value, min, max) { if (min != null) value = Math.max(value, min); if (max != null) value = Math.min(value, max); return value; }
  function formatScore(value) { return Number(value || 0).toFixed(1).replace(/\.0$/, ''); }
  function labelForType(type) { return ({ manual_score: '直接给分', fixed_score: '固定分', tiered_score: '分档计分', count_score: '次数加分', count_deduction: '次数扣分', range_score: '区间计分', matrix_score: '二维查表', tenure_score: '年限分档', fixed_bonus: '固定加分' })[type] || type; }
  function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c])); }
  function escapeAttr(value) { return escapeHtml(value); }
})();
