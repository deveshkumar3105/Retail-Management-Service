const $ = (id) => document.getElementById(id);
const money = (amount, currency='USD') => new Intl.NumberFormat(undefined,{style:'currency',currency,minimumFractionDigits:2}).format(Number(amount));
const date = (value) => new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'numeric'}).format(new Date(value));
const dateTime = (value) => new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
let allOrders=[], filtered=[], page=0; const pageSize=12;
async function loadOrders(){
  try {
    const collected=[]; let offset=0, batch;
    do { const response=await fetch(`/orders?limit=500&offset=${offset}`); if(!response.ok) throw new Error('Could not load orders'); batch=(await response.json()).items; collected.push(...batch); offset+=batch.length; } while(batch.length===500);
    allOrders=collected; $('updated-label').textContent=`Loaded ${allOrders.length.toLocaleString()} orders`;
    updateSummary(); applyFilters();
  } catch(error){$('orders').innerHTML='<tr><td colspan="6" class="empty">Could not load orders. Check that the service is running, then refresh.</td></tr>';toast(error.message);}
}
function updateSummary(){
  $('total-count').textContent=allOrders.length.toLocaleString();
  $('delivered-count').textContent=allOrders.filter(o=>o.order_status==='DELIVERED').length.toLocaleString();
  $('progress-count').textContent=allOrders.filter(o=>['CREATED','CONFIRMED','SHIPPED'].includes(o.order_status)).length.toLocaleString();
  const total=allOrders.reduce((s,o)=>s+Number(o.order_total),0);
  const currency=allOrders[0]?.currency||'USD'; $('total-value').textContent=money(total,currency);
}
function applyFilters(){
  const q=$('search').value.trim().toLowerCase(), status=$('status').value;
  filtered=allOrders.filter(o=>(!status||o.order_status===status)&&(!q||[o.order_id,o.customer_id,...o.items.map(i=>i.product_id)].some(v=>v.toLowerCase().includes(q))));
  page=0; render();
}
function render(){
  const start=page*pageSize, rows=filtered.slice(start,start+pageSize); $('result-count').textContent=`${filtered.length.toLocaleString()}`;
  $('orders').innerHTML=rows.length?rows.map((o,i)=>`<tr class="order-row" data-index="${start+i}" tabindex="0" aria-label="View order ${esc(o.order_id)}"><td class="order-id">${esc(shortId(o.order_id))}</td><td class="customer">${esc(o.customer_id)}</td><td class="date">${date(o.order_timestamp)}</td><td><span class="status status-${o.order_status.toLowerCase()}">${title(o.order_status)}</span></td><td class="right amount">${money(o.order_total,o.currency)}</td><td class="arrow">›</td></tr>`).join(''):'<tr><td colspan="6" class="empty">No orders match. Try a different search or status.</td></tr>';
  $('page-label').textContent=filtered.length?`Showing ${start+1}–${Math.min(start+pageSize,filtered.length)} of ${filtered.length.toLocaleString()}`:'No matching orders';
  $('prev').disabled=page===0; $('next').disabled=(page+1)*pageSize>=filtered.length;
  document.querySelectorAll('.order-row').forEach(row=>{row.addEventListener('click',()=>showOrder(rows[Number(row.dataset.index)-start]));row.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showOrder(rows[Number(row.dataset.index)-start]);}})});
}
function showOrder(o){
  const items=o.items.map(i=>`<tr><td><span class="item-name">${esc(i.product_id)}</span><span class="item-sub">${i.quantity} × ${money(i.unit_price,o.currency)}${Number(i.discount_amount)?` · ${money(i.discount_amount,o.currency)} discount`:''}</span></td><td class="right amount">${money(i.line_total,o.currency)}</td></tr>`).join('');
  $('detail-content').innerHTML=`<div class="detail-head"><p class="eyebrow">ORDER DETAILS</p><h2>${esc(shortId(o.order_id))}</h2><div class="detail-meta"><span class="status status-${o.order_status.toLowerCase()}">${title(o.order_status)}</span><span>Placed ${dateTime(o.order_timestamp)}</span></div></div><div class="detail-body"><dl class="facts"><div><dt>CUSTOMER</dt><dd>${esc(o.customer_id)}</dd></div><div><dt>LAST UPDATED</dt><dd>${dateTime(o.updated_at)}</dd></div><div><dt>RECORD VERSION</dt><dd>${o.source_version}</dd></div></dl><p class="item-title">ITEMS IN THIS ORDER</p><table class="items"><tbody>${items}</tbody></table><div class="total-line"><span>Order total</span><strong>${money(o.order_total,o.currency)}</strong></div></div>`;
  $('detail').showModal();
}
function shortId(id){return id.length>19?id.slice(0,19)+'…':id}
function title(s){return s.charAt(0)+s.slice(1).toLowerCase()}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
let toastTimer;function toast(message){const t=$('toast');t.textContent=message;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),2600)}
$('search').addEventListener('input',applyFilters); $('status').addEventListener('change',applyFilters);
$('prev').addEventListener('click',()=>{page=Math.max(0,page-1);render()}); $('next').addEventListener('click',()=>{page++;render()});
$('detail').querySelector('.close').addEventListener('click',()=>$('detail').close()); $('detail').addEventListener('click',e=>{if(e.target===$('detail'))$('detail').close()});
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('search').focus()}});
loadOrders();
