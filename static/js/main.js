let keyUploaded = false;
let sheetFile = null;

async function uploadKey(input) {
  const file = input.files[0];
  if (!file) return;

  const zone = document.getElementById('keyZone');
  const status = document.getElementById('keyStatus');
  status.className = 'status-msg loading';
  status.textContent = '⏳ Uploading answer key...';

  const formData = new FormData();
  formData.append('answer_key', file);

  try {
    const res = await fetch('/upload-answer-key', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) {
      zone.classList.add('active');
      zone.innerHTML = `
        <div class="upload-inner">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4ECCA3" stroke-width="2">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
          <p><strong>${file.name}</strong></p>
          <span>Subject: ${data.subject}</span>
        </div>`;
      status.className = 'status-msg success';
      status.textContent = '✅ Answer key loaded successfully';
      keyUploaded = true;
    } else {
      status.className = 'status-msg error';
      status.textContent = '❌ ' + data.error;
    }
  } catch (e) {
    status.className = 'status-msg error';
    status.textContent = '❌ Upload failed: ' + e.message;
  }
}

function previewSheet(input) {
  sheetFile = input.files[0];
  if (!sheetFile) return;

  const preview = document.getElementById('sheetPreview');
  const zone = document.getElementById('sheetZone');

  zone.classList.add('active');
  zone.innerHTML = `
    <div class="upload-inner">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4ECCA3" stroke-width="2">
        <path d="M20 6L9 17l-5-5"/>
      </svg>
      <p><strong>${sheetFile.name}</strong></p>
      <span>${(sheetFile.size / 1024).toFixed(1)} KB selected</span>
    </div>`;

  if (sheetFile.type.startsWith('image/')) {
    const reader = new FileReader();
    reader.onload = e => {
      preview.innerHTML = `<img src="${e.target.result}" alt="Preview"/>`;
    };
    reader.readAsDataURL(sheetFile);
  } else {
    preview.innerHTML = `<p style="font-size:0.82rem;color:#555C74;margin-top:8px">📄 PDF ready — preview not available</p>`;
  }
}

async function runEvaluation() {
  if (!keyUploaded) {
    alert('Please upload the answer key first (Step 1).');
    return;
  }
  if (!sheetFile) {
    alert('Please select an answer sheet (Step 2).');
    return;
  }

  const btn = document.getElementById('evalBtn');
  const status = document.getElementById('evalStatus');
  const progressWrap = document.getElementById('progressBar');
  const progressFill = document.getElementById('progressFill');
  const progressLabel = document.getElementById('progressLabel');

  btn.disabled = true;
  btn.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
      style="animation:spin 1s linear infinite">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg> Processing...`;

  status.className = 'status-msg loading';
  status.textContent = 'SAGE is initializing...';
  progressWrap.style.display = 'block';

  const stages = [
    [12,  'ps1', 'Converting PDF to images...'],
    [26,  'ps2', 'Preprocessing & enhancing images...'],
    [45,  'ps3', 'Extracting handwriting via Gemini OCR...'],
    [62,  'ps4', 'Splitting questions (Part A & B)...'],
    [78,  'ps5', 'Grading Part A with AI...'],
    [93,  'ps6', 'Grading Part B with semantic analysis...'],
    [99,  'ps7', 'Compiling results...'],
  ];

  const style = document.createElement('style');
  style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(style);

  let stageIdx = 0;
  const ticker = setInterval(() => {
    if (stageIdx < stages.length) {
      const [pct, id, label] = stages[stageIdx];
      if (stageIdx > 0) {
        document.getElementById(stages[stageIdx - 1][1])?.classList.replace('active', 'done');
      }
      const el = document.getElementById(id);
      if (el) el.classList.add('active');
      progressFill.style.width = pct + '%';
      progressLabel.textContent = label;
      stageIdx++;
    }
  }, 4500);

  try {
    const formData = new FormData();
    formData.append('answer_sheet', sheetFile);

    const res = await fetch('/evaluate', { method: 'POST', body: formData });
    const data = await res.json();

    clearInterval(ticker);
    progressFill.style.width = '100%';
    progressLabel.textContent = '✅ Evaluation complete!';

    for (let i = 1; i <= 7; i++) {
      const el = document.getElementById('ps' + i);
      if (el) { el.classList.remove('active'); el.classList.add('done'); }
    }

    if (data.success) {
      status.className = 'status-msg success';
      status.textContent = '✅ Done! Redirecting to results...';
      setTimeout(() => { window.location.href = data.redirect; }, 1000);
    } else {
      throw new Error(data.error);
    }
  } catch (e) {
    clearInterval(ticker);
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
      </svg> Start Evaluation`;
    progressWrap.style.display = 'none';
    status.className = 'status-msg error';
    status.textContent = '❌ Error: ' + e.message;
  }
}

function toggleSample() {
  const el = document.getElementById('sampleKey');
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function copyKey() {
  const text = document.querySelector('#sampleKey pre').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = '✅ Copied!';
    setTimeout(() => { btn.textContent = '📋 Copy template'; }, 2000);
  });
}