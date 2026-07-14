(() => {
  const fileInput = document.getElementById('dictionary-file');
  const validateButton = document.getElementById('validate-button');
  const importButton = document.getElementById('import-button');
  const confirmRow = document.getElementById('confirm-row');
  const confirmInput = document.getElementById('confirm-import');
  const resultBox = document.getElementById('validation-result');
  const fileName = document.getElementById('file-name');
  let dictionary = null;
  let validation = null;

  const documentFile = document.getElementById('scheme-document-file');
  const documentButton = document.getElementById('ai-document-import');
  const documentName = document.getElementById('scheme-document-name');
  const documentResult = document.getElementById('ai-document-result');
  documentFile.addEventListener('change', () => {
    const file = documentFile.files[0];
    documentButton.disabled = !file;
    documentName.textContent = file ? `${file.name} · ${Math.ceil(file.size / 1024)} KB` : 'PDF / MD，最大 20 MB';
  });
  documentButton.addEventListener('click', async () => {
    const file = documentFile.files[0];
    if (!file) return;
    documentButton.disabled = true;
    documentButton.textContent = 'AI 正在阅读并编写字典…';
    documentResult.hidden = false;
    documentResult.className = 'validation-result';
    documentResult.textContent = '文件较长时可能需要一两分钟，请不要关闭页面。';
    const body = new FormData();
    body.append('file', file);
    try {
      const response = await fetch(window.appUrl('/api/admin/dictionary/from-document'), { method: 'POST', body });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || 'AI 导入失败');
      documentResult.className = 'validation-result valid';
      documentResult.textContent = `已写入 ${result.summary.categories} 个一级指标、${result.summary.items} 个考评明细，正在刷新可视化结构…`;
      setTimeout(() => location.reload(), 900);
    } catch (error) {
      documentResult.className = 'validation-result invalid';
      documentResult.textContent = error.message;
      documentButton.disabled = false;
      documentButton.textContent = '调用 AI 并直接写入';
    }
  });

  fileInput.addEventListener('change', async () => {
    dictionary = null;
    validation = null;
    resultBox.hidden = true;
    confirmRow.hidden = true;
    importButton.hidden = true;
    confirmInput.checked = false;
    const file = fileInput.files[0];
    validateButton.disabled = !file;
    fileName.textContent = file ? `${file.name} · ${Math.ceil(file.size / 1024)} KB` : '最大 3 MB';
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) {
      showResult(false, [{ path: '$', message: '文件不能超过3 MB' }], [], {});
      validateButton.disabled = true;
      return;
    }
    try {
      dictionary = JSON.parse(await file.text());
    } catch (_) {
      showResult(false, [{ path: '$', message: '文件不是合法的 JSON' }], [], {});
      validateButton.disabled = true;
    }
  });

  validateButton.addEventListener('click', async () => {
    if (!dictionary) return;
    validateButton.disabled = true;
    validateButton.textContent = '正在校验…';
    try {
      const response = await fetch(window.appUrl('/api/admin/dictionary/validate'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dictionary),
      });
      validation = await response.json();
      showResult(validation.valid, validation.errors, validation.warnings, validation.summary);
      confirmRow.hidden = !validation.valid;
      importButton.hidden = !validation.valid;
    } catch (error) {
      showResult(false, [{ path: '$', message: error.message }], [], {});
    } finally {
      validateButton.disabled = false;
      validateButton.textContent = '校验并预览';
    }
  });

  confirmInput.addEventListener('change', () => {
    importButton.disabled = !confirmInput.checked;
  });

  importButton.addEventListener('click', async () => {
    if (!dictionary || !validation?.valid || !confirmInput.checked) return;
    importButton.disabled = true;
    importButton.textContent = '正在导入…';
    try {
      const response = await fetch(window.appUrl('/api/admin/dictionary/import'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dictionary, confirmed: true }),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || '导入失败');
      showToast(`已导入 ${result.summary.items} 个考评明细`);
      setTimeout(() => location.reload(), 700);
    } catch (error) {
      showToast(error.message, 'danger');
      importButton.disabled = false;
      importButton.textContent = '确认整套导入';
    }
  });

  function showResult(valid, errors, warnings, summary) {
    resultBox.hidden = false;
    resultBox.className = `validation-result ${valid ? 'valid' : 'invalid'}`;
    const issues = [...(errors || []).map(x => ({ ...x, tone: '错误' })), ...(warnings || []).map(x => ({ ...x, tone: '提醒' }))];
    resultBox.innerHTML = `
      <strong>${valid ? '✓ 格式校验通过' : '× 发现需要修正的问题'}</strong>
      <p>${summary?.categories || 0} 个一级指标 · ${summary?.items || 0} 个明细 · 教师填报 ${summary?.teacher_items || 0} 项 · 管理员录入 ${summary?.admin_items || 0} 项</p>
      ${issues.length ? `<ul class="issue-list">${issues.map(x => `<li><b>${escapeHtml(x.tone)}</b> <code>${escapeHtml(x.path)}</code>：${escapeHtml(x.message)}</li>`).join('')}</ul>` : ''}
    `;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  }
})();
