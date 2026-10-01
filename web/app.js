'use strict';
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => n == null ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2});
const integer = n => Number(n).toLocaleString('en-US');
const currencies = ['THB','USD','EUR','JPY','CNY','GBP','SGD'];
const fields = ['id','name','country','sku','currency','unit_price','moq','pack_size','freight','insurance','other_cost','duty_pct','vat_pct','lead_days','quality_pct','otif_pct','capacity','incoterm','valid_until'];
const numeric = fields.slice(5,17);
const labels = {id:'Quote ID',name:'Supplier name',country:'Country',sku:'Product / SKU',currency:'Quote currency',unit_price:'Unit price',moq:'Minimum order quantity',pack_size:'Pack size',freight:'Freight / shipment',insurance:'Insurance / shipment',other_cost:'Other / shipment',duty_pct:'Duty · %',vat_pct:'VAT · %',lead_days:'Delivery lead · days',quality_pct:'Quality · %',otif_pct:'OTIF · %',capacity:'Available capacity · units',incoterm:'Incoterm (label only)',valid_until:'Quote valid until'};
let quotes = [], token = '', aiAvailable = false, result = null, lastPayload = null, editId = null, requestVersion = 0;
function message(text, kind='success') { const el=$('message'); el.textContent=text;el.className=kind;el.hidden=false; }
function clearMessage(){ $('message').hidden=true; }
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(data)});
  if(!response.ok){ let error;try{error=(await response.json()).error;}catch{}throw Error(error || `Request failed (${response.status}).`); }
  return response;
}
async function action(fn){ clearMessage();try{await fn();}catch(e){message(e.message,'error');} }
function dirty(){ $('dirty').hidden=false; updateWeights(); }
function updateWeights(){ const total=['cost','lead','quality','reliability'].reduce((a,k)=>a+Number($('w-'+k).value),0);$('weight-total').textContent=total+' / 100%'; }
function populate(s){
  const skus=[...new Set(quotes.map(q=>q.sku))];
  $('sku').innerHTML=skus.map(sku=>`<option value="${esc(sku)}">${esc(sku)}</option>`).join('');
  $('sku').value=skus.includes(s.sku)?s.sku:skus[0];
  for(const k of ['quantity','deadline_days','min_quality','min_otif','as_of']) $(k).value=s[k];
  $('vat_recoverable').checked=s.vat_recoverable;
  for(const k of ['cost','lead','quality','reliability']) $('w-'+k).value=s.weights[k];
  $('fx-fields').innerHTML=currencies.map(c=>`<label>${c}<input id="fx-${c}" aria-label="${c} exchange rate" type="number" min="0.000001" max="1000000" step="any" value="${s.fx[c]??({THB:1,USD:35,EUR:38,JPY:.24,CNY:4.9,GBP:45,SGD:26}[c])}" ${c==='THB'?'readonly':''} required></label>`).join('');
  baseline(s.baseline_id);updateWeights();
}
function baseline(id=''){
  $('baseline_id').innerHTML='<option value="">No baseline</option>'+quotes.filter(q=>q.sku===$('sku').value).map(q=>`<option value="${esc(q.id)}">${esc(q.name)} · ${esc(q.id)}</option>`).join('');
  $('baseline_id').value=quotes.some(q=>q.id===id&&q.sku===$('sku').value)?id:'';
}
function scenario(){return {sku:$('sku').value,quantity:Number($('quantity').value),deadline_days:Number($('deadline_days').value),min_quality:Number($('min_quality').value),min_otif:Number($('min_otif').value),as_of:$('as_of').value,vat_recoverable:$('vat_recoverable').checked,baseline_id:$('baseline_id').value,weights:Object.fromEntries(['cost','lead','quality','reliability'].map(k=>[k,Number($('w-'+k).value)])),fx:Object.fromEntries(currencies.map(k=>[k,Number($('fx-'+k).value)]))};}
async function compare(candidate=quotes,s=scenario()){
  const version=++requestVersion;
  const payload=structuredClone({quotes:candidate,scenario:s});
  $('analyze-btn').disabled=true;$('analyze-btn').textContent='Calculating…';
  try{
    const data=await (await api('/api/analyze',payload)).json();
    if(version!==requestVersion)return;
    quotes=payload.quotes;result=data;lastPayload=payload;
    render();$('dirty').hidden=JSON.stringify(scenario())===JSON.stringify(payload.scenario);
    $('sensitivity-results').innerHTML='<div class="empty">Run scenarios to compare the latest successful analysis.</div>';
  }finally{if(version===requestVersion){$('analyze-btn').disabled=false;$('analyze-btn').textContent='Run comparison';}}
}
function metric(label,value,note){return `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-note">${note}</div></div>`;}
function render(){
 const r=result,w=r.results.find(q=>q.id===r.winner_id),eligible=r.results.filter(q=>q.eligible),delta=r.baseline_delta;
 let html='<div class="metrics">'+metric('Recommended landed cost',w?fmt(w.landed_cost):'No award','THB · '+(r.scenario.vat_recoverable?'excluding recoverable VAT':'including non-recoverable VAT'))+metric('Eligible suppliers',`${r.eligible_count}<span>/ ${r.results.length}</span>`,'Meets every purchase requirement')+metric('Cost vs. selected baseline',delta===null?'—':`${delta>=0?'−':'+'}${fmt(Math.abs(delta))}`,delta===null?'Choose a baseline in advanced settings':delta>=0?'THB lower · modeled difference':'THB higher · modeled difference')+metric('Recommended lead time',w?`${w.lead_days}<span>days</span>`:'—',`Required within ${r.scenario.deadline_days} calendar days`)+'</div>';
 html+=w?`<div class="recommendation"><div class="rec-symbol">✓</div><div><div class="eyebrow">RECOMMENDED FOR REVIEW</div><h2>${esc(w.name)}</h2><p>${esc(w.country)} · ${integer(w.ordered_qty)} units · Quality ${w.quality_pct}% · OTIF ${w.otif_pct}%</p></div><div class="rec-score">${fmt(w.score)}<small>WEIGHTED SCORE / 100</small></div></div>`:`<div class="recommendation"><div><div class="eyebrow">NO ELIGIBLE SUPPLIER</div><h2>No award recommended</h2><p>Review exclusions below or revise requirements. A low price cannot override an unmet constraint.</p></div></div>`;
 html+=`<div class="panel table-panel"><div class="section-top"><div><h2>Supplier comparison</h2><p>${esc(r.scenario.sku)} · ${integer(r.scenario.quantity)} required units · ${esc(r.scenario.as_of)}</p></div><div class="quote-tools"><a href="/api/template" download>CSV template</a><button class="secondary" id="add-quote">Add quote</button></div></div><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Supplier / quote</th><th>Landed cost · THB</th><th>Lead time</th><th>Quality / OTIF</th><th>Score</th><th>Status</th><th><span class="muted">Edit</span></th></tr></thead><tbody>`;
 html+=r.results.map(q=>`<tr class="${q.id===r.winner_id?'winner-row':!q.eligible?'excluded-row':''}"><td><span class="rank">${q.rank??'—'}</span></td><td><span class="supplier-name">${esc(q.name)}</span><span class="supplier-sub">${esc(q.id)} · ${esc(q.currency)} ${fmt(q.unit_price)} / unit · ${esc(q.incoterm)}</span></td><td><strong>${fmt(q.landed_cost)}</strong><br><span class="supplier-sub">${integer(q.ordered_qty)} ordered · ${q.excess_qty?integer(q.excess_qty)+' excess':'no excess'}</span></td><td>${q.lead_days} days</td><td>${q.quality_pct}% / ${q.otif_pct}%</td><td class="score">${q.score===null?'—':fmt(q.score)}</td><td>${q.eligible?'<span class="badge">Eligible</span>':`<span class="badge excluded">Excluded</span><br><span class="supplier-sub">${q.reasons.map(esc).join('<br>')}</span>`}</td><td><button class="edit-button" data-edit="${esc(q.id)}" aria-label="Edit ${esc(q.name)}">Edit</button></td></tr>`).join('');
 html+='</tbody></table></div><div class="table-note">Sorted by feasibility, then weighted score. Costs include MOQ / pack-size effects. All amounts are modeled.</div></div>';
 html+='<div class="split"><div class="panel"><div class="section-top"><h2>Landed cost breakdown</h2><span class="muted">Eligible offers · THB</span></div>';
 if(!eligible.length)html+='<div class="empty">No eligible offers to chart.</div>';
 else{
 const max=Math.max(...eligible.map(q=>q.landed_cost));
 html+='<div class="bars">'+eligible.map(q=>{const values=[q.goods_thb,q.freight_thb+q.insurance_thb,q.duty_thb+(r.scenario.vat_recoverable?0:q.vat_thb),q.other_thb];return `<div class="bar-row"><div class="bar-head"><span>${esc(q.name)}</span><strong>${fmt(q.landed_cost)}</strong></div><div class="bar-track" role="img" aria-label="${esc(q.name)}: goods ${fmt(values[0])}, logistics ${fmt(values[1])}, taxes ${fmt(values[2])}, other ${fmt(values[3])} THB">${values.map((v,i)=>`<span class="${['goods','logistics','tax','other'][i]}" style="width:${100*v/max}%" title="${['Goods','Freight + insurance','Duty + non-recoverable VAT','Other'][i]}: THB ${fmt(v)}"></span>`).join('')}</div></div>`;}).join('')+'</div><div class="legend"><span style="--c:#1e776f">Goods</span><span style="--c:#69b4a5">Freight + insurance</span><span style="--c:#b2d8cb">Taxes in cost</span><span style="--c:#d7e5e9">Other</span></div>';
 }
 html+='</div><div class="panel"><div class="insight-head"><h2>Decision brief</h2><span class="pill">RULE-BASED</span></div><div class="brief">'+esc(r.brief)+'</div></div></div>';
 html+=`<div class="panel"><div class="section-top"><h2>Evidence & next steps</h2><span class="muted">Human approval required</span></div><details><summary>View score components and cash outlay</summary><div class="table-wrap"><table><thead><tr><th>Supplier</th><th>Cost score</th><th>Lead score</th><th>Quality</th><th>Reliability</th><th>Cash outlay · THB</th><th>Watch points</th></tr></thead><tbody>${r.results.map(q=>`<tr><td>${esc(q.name)}</td>${['cost','lead','quality','reliability'].map(k=>`<td>${fmt(q.components[k])}</td>`).join('')}<td>${fmt(q.cash_outlay)}</td><td>${q.flags.map(esc).join('<br>')||'None in this model'}</td></tr>`).join('')}</tbody></table></div></details><div class="export-actions"><button class="secondary" data-export="csv">Export comparison CSV</button><button class="secondary" data-export="html">Download printable report</button><button class="secondary" data-export="json">Export calculation JSON</button></div><div class="ai-box"><div class="insight-head"><h3>AI explanation</h3><span class="pill">${aiAvailable?'API CONFIGURED':'OPTIONAL · NOT CONFIGURED'}</span></div><p>${aiAvailable?'Ask for a negotiation brief or an explanation in Thai. The model cannot change the calculated ranking.':'The full comparison works offline. To enable AI, set OPENAI_API_KEY and OPENAI_MODEL before starting the app. See README for setup.'}</p><label>Business question (optional)<textarea id="ai-question" maxlength="500" placeholder="Explain the trade-offs and suggest negotiation questions in Thai." ${!aiAvailable?'disabled':''}></textarea></label><label class="check"><input type="checkbox" id="ai-consent" ${!aiAvailable?'disabled':''}>I agree to send this analysis and question to OpenAI. API charges may apply.</label><button id="ai-btn" class="primary" ${!aiAvailable?'disabled':''}>Generate AI explanation</button><div id="ai-output" class="ai-text" aria-live="polite"></div></div></div>`;
 $('results-area').innerHTML=html;
 $('assumptions').innerHTML='<ul class="assumptions">'+r.assumptions.map(a=>'<li>'+esc(a)+'</li>').join('')+'</ul>';
 $('add-quote').onclick=()=>openQuote();
 document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>openQuote(b.dataset.edit));
 document.querySelectorAll('[data-export]').forEach(b=>b.onclick=()=>action(()=>download(b.dataset.export)));
 $('ai-btn').onclick=()=>action(async()=>{
   if(!$('ai-consent').checked)throw Error('Confirm consent before sending data to OpenAI.');
   if(!$('dirty').hidden)throw Error('Run comparison first to use your changed inputs.');
   const button=$('ai-btn');button.disabled=true;button.textContent='Generating…';
   try{const response=await (await api('/api/explain',{...lastPayload,question:$('ai-question').value,consent:true})).json();$('ai-output').textContent=response.mode+'\n\n'+response.text;}
   finally{button.disabled=false;button.textContent='Generate AI explanation';}
 });
}
function openQuote(id=null){
 editId=id;
 const q=id?quotes.find(q=>q.id===id):{id:'Q'+Date.now().toString().slice(-7),name:'New supplier',country:'Thailand',sku:$('sku').value,currency:'THB',unit_price:100,moq:1,pack_size:1,freight:0,insurance:0,other_cost:0,duty_pct:0,vat_pct:7,lead_days:7,quality_pct:98,otif_pct:95,capacity:10000,incoterm:'FCA',valid_until:'2030-12-31'};
 $('quote-title').textContent=id?'Edit supplier quote':'Add supplier quote';
 $('remove-quote').hidden=!id;
 $('quote-fields').innerHTML=fields.map(k=>{
 let input;
 if(k==='currency'||k==='incoterm'){const opts=k==='currency'?currencies:['EXW','FCA','FOB','CFR','CIF','CPT','CIP','DAP','DPU','DDP','FAS'];input=`<select name="${k}">${opts.map(o=>`<option ${q[k]===o?'selected':''}>${o}</option>`).join('')}</select>`;}
 else input=`<input name="${k}" value="${esc(q[k])}" type="${numeric.includes(k)?'number':k==='valid_until'?'date':'text'}" ${numeric.includes(k)?`step="${['moq','pack_size','lead_days','capacity'].includes(k)?'1':'any'}" min="${['moq','pack_size','lead_days','capacity'].includes(k)?'1':k==='unit_price'?'0.000001':'0'}" max="${k.endsWith('_pct')?'100':'1000000'}"`:'maxlength="100"'} ${k==='id'&&id?'readonly':''} required>`;
 return `<label>${labels[k]}${input}</label>`;
 }).join('');$('quote-dialog').showModal();
}
async function download(format){
 if(!lastPayload)throw Error('Run a comparison first.');
 if(!$('dirty').hidden)throw Error('Run comparison first to export your changed inputs.');
 const response=await api('/api/export',{...lastPayload,format});
 const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download={csv:'supplier-comparison.csv',html:'procurement-report.html',json:'procurement-analysis.json'}[format];document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);
}
async function history(){
 const items=await (await api('/api/history')).json();
 $('history-list').className=items.length?'':'empty';
 $('history-list').innerHTML=items.length?items.map(i=>`<div class="history-item"><div><strong>${esc(i.title)}</strong><p>${esc(new Date(i.created_at).toLocaleString())} · Snapshot #${i.id}</p><small>SHA-256 ${esc(i.sha256.slice(0,24))}…</small></div><button class="secondary" data-load="${i.id}">Load decision</button></div>`).join(''):'No saved decisions yet. Compare suppliers, then choose Save decision.';
 document.querySelectorAll('[data-load]').forEach(b=>b.onclick=()=>action(async()=>{
  const snapshot=await (await api('/api/history/'+b.dataset.load)).json();quotes=snapshot.quotes;populate(snapshot.scenario);await compare();switchView('compare');message('Saved inputs loaded and recalculated with engine v1.0.0.');
 }));
}
function switchView(name){document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==name);document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('active',b.dataset.view===name));$('breadcrumb').textContent={compare:'Supplier comparison',scenarios:'Scenario lab',history:'Saved decisions',method:'Methodology'}[name];if(name==='history')action(history);}
$('scenario-form').addEventListener('input',dirty);
$('scenario-form').addEventListener('change',dirty);
$('sku').addEventListener('change',()=>baseline());
$('scenario-form').onsubmit=e=>{e.preventDefault();action(()=>compare());};
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
$('close-quote').onclick=()=>$('quote-dialog').close();
$('quote-form').onsubmit=e=>{e.preventDefault();action(async()=>{
 const q=Object.fromEntries(new FormData(e.target));for(const k of numeric)q[k]=Number(q[k]);
 const candidate=editId?quotes.map(x=>x.id===editId?q:x):[...quotes,q];
 const s=scenario();if(editId&&q.sku!==s.sku){s.sku=q.sku;s.baseline_id='';}
 await compare(candidate,s);populate(s);$('dirty').hidden=true;$('quote-dialog').close();message('Quote updated and comparison recalculated.');
 });};
$('remove-quote').onclick=()=>action(async()=>{
 if(!confirm('Remove this quote from the current workspace? Saved snapshots will remain.'))return;
 const candidate=quotes.filter(q=>q.id!==editId);if(!candidate.length)throw Error('Keep at least one quote.');
 const s=scenario();if(s.baseline_id===editId)s.baseline_id='';if(!candidate.some(q=>q.sku===s.sku)){s.sku=candidate[0].sku;s.baseline_id='';}
 await compare(candidate,s);populate(s);$('dirty').hidden=true;$('quote-dialog').close();
});
$('import-btn').onclick=()=>$('csv-file').click();
$('csv-file').onchange=e=>action(async()=>{
 const file=e.target.files[0];if(!file)return;if(file.size>500000)throw Error('CSV must be below 500 KB.');
 const data=await (await api('/api/import',{csv:await file.text()})).json();
 if(!confirm(`Replace the current quotes with ${data.quotes.length} validated CSV quotes? Saved decisions remain.`)){e.target.value='';return;}
 const s=scenario();if(!data.quotes.some(q=>q.sku===s.sku))s.sku=data.quotes[0].sku;
 s.baseline_id='';await compare(data.quotes,s);populate(s);$('dirty').hidden=true;e.target.value='';message(`Imported ${data.quotes.length} quotes successfully.`);
});
$('reset-btn').onclick=()=>action(async()=>{if(!confirm('Reset current inputs to the synthetic demo? Saved decisions remain.'))return;const data=await (await api('/api/bootstrap')).json();quotes=data.quotes;populate(data.scenario);await compare();message('Demo restored.');});
$('save-btn').onclick=()=>{if(!lastPayload)return message('Run a comparison first.','error');if(!$('dirty').hidden)return message('Run comparison before saving changed inputs.','error');$('save-title').value=`${result.scenario.sku} · ${integer(result.scenario.quantity)} units`;$('save-dialog').showModal();};
$('cancel-save').onclick=()=>$('save-dialog').close();
$('save-form').onsubmit=e=>{e.preventDefault();action(async()=>{const data=await (await api('/api/save',{...lastPayload,title:$('save-title').value})).json();$('save-dialog').close();message(`Decision #${data.id} saved with its inputs, results and SHA-256 checksum.`);});};
$('sensitivity-btn').onclick=()=>action(async()=>{
 if(!lastPayload)throw Error('Run a comparison first.');if(!$('dirty').hidden)throw Error('Run comparison first to use your changed inputs.');
 const button=$('sensitivity-btn');button.disabled=true;
 try{const cases=await (await api('/api/sensitivity',lastPayload)).json();$('sensitivity-results').className='';$('sensitivity-results').innerHTML=cases.map(c=>`<div class="scenario-card"><div><strong>${esc(c.label)}</strong><small>${integer(c.quantity)} required units</small></div><div>${esc(c.winner||'No eligible supplier')}<small>${c.eligible_count} eligible suppliers</small></div><div><strong>${fmt(c.landed_cost)}</strong><small>Landed cost · THB</small></div><span class="badge ${c.changed?'excluded':''}">${c.changed?'Recommendation changes':'Recommendation holds'}</span></div>`).join('');}
 finally{button.disabled=false;}
});
action(async()=>{const data=await (await api('/api/bootstrap')).json();token=data.token;quotes=data.quotes;aiAvailable=data.ai_available;populate(data.scenario);await compare();});
