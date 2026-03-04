const pendingOverrides = {};

function markChanged(input) {
  const q = input.dataset.q;
  const max = parseInt(input.dataset.max);
  let val = parseInt(input.value);

  if (isNaN(val) || val < 0) val = 0;
  if (val > max) val = max;
  input.value = val;

  input.classList.add('changed');
  pendingOverrides[q] = val;
  document.getElementById('overrideBar').style.display = 'flex';
}

async function saveOverrides() {
  if (Object.keys(pendingOverrides).length === 0) return;

  const bar = document.getElementById('overrideBar');
  bar.innerHTML = '<span>⏳ Saving overrides...</span>';

  try {
    const res = await fetch('/override', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: SESSION_ID, overrides: pendingOverrides })
    });
    const data = await res.json();

    if (data.success) {
      const t = data.totals;
      document.getElementById('partATotal').textContent = t.part_a_total;
      document.getElementById('partBTotal').textContent = t.part_b_total;
      document.getElementById('grandTotal').textContent = t.grand_total;
      document.getElementById('partATotalLabel').textContent = t.part_a_total;
      document.getElementById('partBTotalLabel').textContent = t.part_b_total;
      document.getElementById('gradeDisplay').textContent = t.grade;
      document.getElementById('pctDisplay').textContent = t.percentage;

      document.querySelectorAll('.mark-input.changed').forEach(inp => {
        inp.classList.remove('changed');
        const wrapper = inp.parentElement;
        if (!wrapper.querySelector('.override-chip')) {
          const tag = document.createElement('span');
          tag.className = 'override-chip';
          tag.textContent = '✎';
          wrapper.appendChild(tag);
        }
      });

      bar.innerHTML = `
        <span style="color:var(--green)">✅ Saved! New total: <strong>${t.grand_total}/60</strong> (${t.percentage}%)</span>
        <button class="save-override-btn" onclick="window.location.href='/report/${SESSION_ID}'">
          ⬇ Download Report
        </button>`;
      bar.style.background = 'rgba(78,204,163,0.08)';
      bar.style.borderColor = 'rgba(78,204,163,0.3)';

    } else {
      bar.innerHTML = `<span>❌ ${data.error}</span>
        <button class="save-override-btn" onclick="saveOverrides()">Retry</button>`;
    }
  } catch (e) {
    bar.innerHTML = `<span>❌ ${e.message}</span>
      <button class="save-override-btn" onclick="saveOverrides()">Retry</button>`;
  }
}