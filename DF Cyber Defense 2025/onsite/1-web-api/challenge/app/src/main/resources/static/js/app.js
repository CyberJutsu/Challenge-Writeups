const $ = (q) => document.querySelector(q);
const statusEl = $('#status');
const resultsEl = $('#results');

function renderResults(list){
  resultsEl.innerHTML = '';
  if(!Array.isArray(list) || list.length === 0){
    resultsEl.innerHTML = '<div class="result">No results</div>';
    return;
  }
  list.forEach(it => {
    const el = document.createElement('div');
    el.className = 'result';
    const categories = Array.isArray(it.categories) ? it.categories.map(escapeHtml).join(', ') : '';
    const transactionDate = it.transactionDate ? new Date(it.transactionDate).toLocaleDateString() : '';
    const amount = it.amount ? `$${it.amount.toFixed(2)}` : '';
    const amountClass = it.transactionType === 'CREDIT' ? 'credit' : 'debit';
    
    el.innerHTML = `
      <div class="title">${escapeHtml(it.customerName || '')} • Account: ${escapeHtml(it.accountNumber || '')}</div>
      <div class="meta transaction-info">
        <span class="type">${escapeHtml(it.transactionType || '')}</span>
        <span class="date">${escapeHtml(transactionDate)}</span>
        <span class="amount ${amountClass}">${amount}</span>
      </div>
      <div class="meta description">${escapeHtml(it.description || '')} at ${escapeHtml(it.merchantName || '')}</div>
      <div class="meta status-line">Status: ${escapeHtml(it.status || 'UNKNOWN')}</div>
      <div class="meta categories">Categories: ${categories}</div>
    `;
    resultsEl.appendChild(el);
  });
}

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
}

async function searchWithParams(params){
  statusEl.textContent = 'Searching transactions...';
  try{
    const res = await fetch(`/api/statements/search?${params.toString()}`);
    const data = await res.json();
    renderResults(data);
    statusEl.textContent = `Found ${data.length} transaction(s)`;
  }catch(e){
    statusEl.textContent = 'Error';
    resultsEl.innerHTML = `<div class="result">${escapeHtml(String(e))}</div>`;
  }
}

document.getElementById('form-search').addEventListener('submit', (ev) => {
  ev.preventDefault();

  const params = new URLSearchParams();
  const customerName = document.getElementById('customerName').value.trim();
  const merchantName = document.getElementById('merchantName').value.trim();
  const transactionDate = document.getElementById('transactionDate').value.trim();
  const transactionType = document.getElementById('transactionType').value;

  if (customerName) params.append('customerName', customerName);
  if (merchantName) params.append('merchantName', merchantName);
  if (transactionDate) params.append('transactionDate', transactionDate);
  if (transactionType) params.append('transactionType', transactionType);

  if (params.toString()) {
    searchWithParams(params);
  } else {
    loadAllStatements();
  }
});

async function loadAllStatements(){
  statusEl.textContent = 'Loading statements...';
  try{
    const res = await fetch('/api/statements/');
    const data = await res.json();
    renderResults(data);
    statusEl.textContent = `Showing ${data.length} statements`;
  }catch(e){
    statusEl.textContent = 'Error loading statements';
    resultsEl.innerHTML = `<div class="result">Failed to load statements</div>`;
  }
}

loadAllStatements();