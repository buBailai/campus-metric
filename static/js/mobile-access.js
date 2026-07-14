(() => {
  const baseInput = document.getElementById('qr-base-url');
  const regenerate = document.getElementById('regenerate-qr');
  const cards = [...document.querySelectorAll('.qr-card')];

  function normalizedBase() {
    return baseInput.value.trim().replace(/\/$/, '');
  }

  function render() {
    const base = normalizedBase();
    if (!/^https?:\/\//i.test(base)) {
      showToast('请输入以 http:// 或 https:// 开头的地址', 'danger');
      return;
    }
    cards.forEach(card => {
      const url = `${base}${card.dataset.path}`;
      const box = card.querySelector('.qr-code');
      box.innerHTML = '';
      new QRCode(box, { text: url, width: 102, height: 102, colorDark: '#15171a', colorLight: '#ffffff', correctLevel: QRCode.CorrectLevel.M });
      card.querySelector('.qr-url').textContent = url;
      card.dataset.url = url;
    });
  }

  regenerate.addEventListener('click', () => {
    render();
    showToast('二维码已按新地址生成');
  });

  cards.forEach(card => {
    card.querySelector('[data-copy]').addEventListener('click', async () => {
      const value = card.dataset.url || '';
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(value);
        } else {
          const helper = document.createElement('textarea');
          helper.value = value;
          helper.setAttribute('readonly', '');
          helper.style.position = 'fixed';
          helper.style.opacity = '0';
          document.body.appendChild(helper);
          helper.select();
          if (!document.execCommand('copy')) throw new Error('copy failed');
          helper.remove();
        }
        showToast('访问链接已复制');
      } catch (_) {
        const link = card.querySelector('.qr-url');
        const range = document.createRange();
        range.selectNodeContents(link);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        showToast('浏览器限制了自动复制，链接已选中，请长按复制', 'danger');
      }
    });
  });

  render();
})();
