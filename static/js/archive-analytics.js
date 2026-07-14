(() => {
  const type = document.getElementById('analytics-type');
  const teacherWrap = document.getElementById('teacher-filter');
  const classWrap = document.getElementById('class-filter');
  const teacherSelect = document.getElementById('analytics-teacher');
  const classSelect = document.getElementById('analytics-class');
  const loadButton = document.getElementById('analytics-load');
  const loadStatus = document.getElementById('analytics-load-status');
  const detailModal = document.getElementById('archive-detail-modal');
  const detailContent = document.getElementById('archive-modal-content');
  let details = [];
  type.addEventListener('change', () => {
    const teacherMode = type.value === 'teacher';
    teacherSelect.disabled = !teacherMode;
    classSelect.disabled = teacherMode;
    teacherWrap.classList.toggle('is-disabled', !teacherMode);
    classWrap.classList.toggle('is-disabled', teacherMode);
  });
  loadButton.addEventListener('click', load);
  load();

  async function load() {
    const value = type.value === 'teacher' ? teacherSelect.value : classSelect.value;
    if (!value) {
      loadStatus.textContent = type.value === 'teacher' ? '当前没有可选择的教师。' : '当前还没有带班级信息的已通过记录。';
      showToast(loadStatus.textContent, 'danger');
      return;
    }
    const params = new URLSearchParams({ entity_type: type.value, entity_value: value || '' });
    const start = document.getElementById('analytics-start').value;
    const end = document.getElementById('analytics-end').value;
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    loadButton.disabled = true;
    loadButton.textContent = '正在生成…';
    loadStatus.textContent = '正在读取全部可访问方案及所有学年的已通过数据…';
    try {
      const response = await fetch(window.appUrl(`/api/admin/archive-analytics?${params}`));
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || '档案数据读取失败');
      renderSummary(data.summary);
      renderTrend(data.timeline);
      renderBars('compare-chart', data.comparison);
      renderBars('category-chart', data.categories);
      renderDetails(data.details || []);
      loadStatus.textContent = `档案视图已生成：${data.summary.records || 0} 条有效记录，覆盖 ${data.summary.schemes || 0} 套方案。`;
    } catch (error) {
      loadStatus.textContent = `生成失败：${error.message}`;
      showToast(error.message, 'danger');
    } finally {
      loadButton.disabled = false;
      loadButton.textContent = '生成档案视图';
    }
  }

  function renderSummary(row) {
    document.getElementById('analytics-summary').innerHTML = [
      ['跟踪对象', row.label || '—'], ['累计得分', row.score ?? 0], ['有效记录', row.records ?? 0],
      ['覆盖方案', row.schemes ?? 0], ['覆盖学年', row.years ?? 0], ['归档记录', row.archived_records ?? 0],
    ].map(([label, value]) => `<article><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></article>`).join('');
  }

  function renderTrend(rows) {
    const box = document.getElementById('trend-chart');
    if (!rows.length) { box.innerHTML = '<div class="empty-state"><p>该范围内暂无已通过数据</p></div>'; return; }
    const width = 720, height = 250, pad = 34, max = Math.max(...rows.map(row => row.score), 1);
    const points = rows.map((row, index) => {
      const x = pad + (rows.length === 1 ? (width - pad * 2) / 2 : index * (width - pad * 2) / (rows.length - 1));
      const y = height - pad - row.score / max * (height - pad * 2);
      return { ...row, x, y };
    });
    const area = `${points.map(p => `${p.x},${p.y}`).join(' ')} ${points.at(-1).x},${height - pad} ${points[0].x},${height - pad}`;
    box.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="月度得分趋势"><polygon class="trend-area" points="${area}"/><polyline class="trend-line" points="${points.map(p => `${p.x},${p.y}`).join(' ')}"/>${points.map(p => `<circle cx="${p.x}" cy="${p.y}" r="5"><title>${escapeHtml(p.label)}：${p.score}</title></circle><text x="${p.x}" y="${height - 9}" text-anchor="middle">${escapeHtml(p.label)}</text>`).join('')}</svg>`;
  }

  function renderBars(id, rows) {
    const box = document.getElementById(id);
    if (!rows.length) { box.innerHTML = '<div class="empty-state"><p>暂无可对比数据</p></div>'; return; }
    const max = Math.max(...rows.map(row => Math.abs(row.score)), 1);
    box.innerHTML = rows.map(row => `<div class="bar-row"><span title="${escapeHtml(row.label)}">${escapeHtml(row.label)}</span><i><b style="width:${Math.max(2, Math.abs(row.score) / max * 100)}%"></b></i><strong>${row.score}</strong></div>`).join('');
  }
  function renderDetails(rows) {
    details = rows;
    const box = document.getElementById('archive-detail-list');
    if (!rows.length) { box.innerHTML = '<div class="empty-state"><p>该范围内暂无评价明细</p></div>'; return; }
    box.innerHTML = rows.map((row, index) => `<button class="archive-detail-row" type="button" data-detail-index="${index}"><strong>${escapeHtml(row.indicator)}</strong><span>${escapeHtml(row.teacher)} · ${escapeHtml(row.year)}</span><small>${escapeHtml(row.scheme_code)} · ${escapeHtml(row.created_at)}</small><b>${escapeHtml(row.score)} 分</b></button>`).join('');
    box.querySelectorAll('[data-detail-index]').forEach(button => button.addEventListener('click', () => openDetail(Number(button.dataset.detailIndex))));
  }
  function openDetail(index) {
    const row = details[index];
    if (!row) return;
    const fields = [...(row.input_fields || [])];
    if (row.tracking) fields.push({ label: row.tracking_label || '班级', value: row.tracking });
    detailContent.innerHTML = `<div class="archive-modal-title"><div class="eyebrow">${escapeHtml(row.category)}</div><h2>${escapeHtml(row.indicator)}</h2></div><div class="archive-modal-meta"><span>${escapeHtml(row.teacher)}</span><span>${escapeHtml(row.scheme_code)} · ${escapeHtml(row.scheme)}</span><span>${escapeHtml(row.year)}</span><span>${escapeHtml(row.created_at)}</span><span>${escapeHtml(row.score)} 分</span></div><div class="archive-modal-fields">${fields.length ? fields.map(field => `<span><small>${escapeHtml(field.label)}</small><strong>${escapeHtml(field.value)}</strong></span>`).join('') : '<span><small>填报字段</small><strong>无</strong></span>'}</div>${row.note ? `<div class="archive-modal-note"><strong>补充说明</strong>\n${escapeHtml(row.note)}</div>` : ''}${(row.attachments || []).length ? `<div class="archive-modal-attachments">${row.attachments.map(item => `<img src="${escapeAttr(item.url)}" alt="${escapeAttr(item.name)}">`).join('')}</div>` : ''}`;
    detailModal.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeDetail() {
    detailModal.hidden = true;
    detailContent.innerHTML = '';
    document.body.style.overflow = '';
  }
  document.getElementById('archive-modal-close').addEventListener('click', closeDetail);
  detailModal.addEventListener('click', event => { if (event.target === detailModal) closeDetail(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !detailModal.hidden) closeDetail(); });
  function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[c])); }
  function escapeAttr(value) { return escapeHtml(value); }
})();
