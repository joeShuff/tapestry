const $=(s,e=document)=>e.querySelector(s);
const h=(t,a,...k)=>{const e=document.createElement(t);if(a===null||a===undefined||typeof a!=='object'||a instanceof Node||Array.isArray(a)){if(a!=null)k.unshift(a);a={}}
  for(const[n,v]of Object.entries(a))n.startsWith('on')?e.addEventListener(n.slice(2),v):n==='class'?e.className=v:e.setAttribute(n,v);
  e.append(...k.flat().filter(x=>x!=null&&x!==false));return e};
async function api(p,o={}){const r=await fetch('/api/v1'+p,o);if(!r.ok){let m=r.statusText;try{m=(await r.json()).detail||m}catch{}throw new Error(typeof m==='string'?m:'Something went wrong')}return r.status===204?null:r.json()}
const json=(method,b)=>({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});
const ago=t=>{const s=Math.max(0,Date.now()/1e3-t);return s<60?'just now':s<3600?Math.floor(s/60)+' min ago':s<86400?Math.floor(s/3600)+' h ago':new Date(t*1e3).toLocaleDateString()};
const size=n=>n>1e6?(n/1e6).toFixed(1)+' MB':Math.max(1,Math.round(n/1e3))+' KB';
function toast(m,bad){const t=$('#toast');t.textContent=m;t.className='show'+(bad?' bad':'');clearTimeout(toast.id);toast.id=setTimeout(()=>t.className='',3200)}
const act=async(fn,ok)=>{try{await fn();if(ok)toast(ok);await load()}catch(e){toast(e.message,1)}};

let S={tab:'waiting',files:[],maps:[],failed:[]};
async function load(){[S.files,S.maps,S.failed]=await Promise.all([api('/files'),api('/mappings'),api('/failed')]);render()}
function render(){
  const tabs=[['waiting','Waiting',S.failed.length],['cards','Cards',S.maps.length],['audio','Audio',S.files.length]];
  $('#tabs').replaceChildren(...tabs.map(([k,l,n])=>h('button',{class:k===S.tab?'on':'',onclick:()=>{S.tab=k;render()}},l,h('span',{class:'n'+(k==='waiting'&&n?' hot':'')},n))));
  $('#view').replaceChildren(...({waiting:vWaiting,cards:vCards,audio:vAudio}[S.tab])().flat());
}

const vWaiting=()=>[
  h('p',{class:'lead'},'Cards the player scanned but could not find. Tap a card on the player and it appears here, ready to assign.'),
  S.failed.length?h('div',{class:'grid'},S.failed.map(f=>h('div',{class:'tag'},
    h('button',{class:'x',title:'Dismiss','aria-label':'Dismiss '+f.uid,onclick:()=>act(()=>api('/failed/'+f.uid,{method:'DELETE'}))},'×'),
    h('div',{class:'uid'},f.uid),
    h('div',{class:'meta'},Date.now()/1e3-f.last_seen<30?h('span',{class:'live'},'Just scanned'):'Last scan '+ago(f.last_seen),f.count>1?', '+f.count+' scans':''),
    h('button',{class:'btn',onclick:()=>assign({uid:f.uid})},'Assign audio'))))
  :h('div',{class:'empty'},'Nothing waiting. Unknown cards show up here as soon as they are scanned.')];

const vCards=()=>[
  h('div',{class:'top'},h('p',{class:'lead',style:'margin:0'},'Every card that plays something.'),h('button',{class:'btn',onclick:()=>assign({})},'Add card')),
  S.maps.length?S.maps.map(m=>h('div',{class:'row'},
    h('div',{class:'main'},h('div',{class:'t'},m.label||m.file_title),h('div',{class:'m'},h('span',{class:'mono'},m.uid),m.label?', plays '+m.file_title:'')),
    h('div',{class:'acts'},
      h('button',{class:'ghost',onclick:()=>assign({uid:m.uid,label:m.label,file_id:m.file_id})},'Change'),
      h('button',{class:'ghost danger',onclick:()=>confirm('Remove this card? It will show up under Waiting next time it is scanned.')&&act(()=>api('/mappings/'+m.uid,{method:'DELETE'}),'Card removed')},'Remove'))))
  :h('div',{class:'empty'},'No cards assigned yet. Add one here, or assign a scanned card under Waiting.')];

const vAudio=()=>[
  h('div',{class:'top'},h('p',{class:'lead',style:'margin:0'},'Audio files stored on this server.'),h('button',{class:'btn',onclick:upload},'Upload audio')),
  S.files.length?S.files.map(f=>h('div',{class:'row'},
    h('div',{class:'main'},h('div',{class:'t'},f.title),
      h('div',{class:'m'},f.filename+', '+size(f.size)+', '+(f.uses?f.uses+(f.uses>1?' cards':' card'):'not on any card')),
      h('div',{class:'m mono'},'sha256 '+f.sha256.slice(0,12)),
      h('audio',{controls:'',preload:'none',src:f.download_url})),
    h('div',{class:'acts'},
      h('button',{class:'ghost',onclick:()=>{const t=prompt('New title',f.title);if(t&&t.trim())act(()=>api('/files/'+f.id,json('PATCH',{title:t})),'Renamed')}},'Rename'),
      h('button',{class:'ghost',onclick:()=>replaceFile(f)},'Replace file'),
      h('button',{class:'ghost danger',onclick:()=>confirm(f.uses?`Delete "${f.title}"? ${f.uses} card${f.uses>1?'s':''} will stop working.`:`Delete "${f.title}"?`)&&act(()=>api('/files/'+f.id,{method:'DELETE'}),'Deleted')},'Delete'))))
  :h('div',{class:'empty'},'No audio yet. Upload an MP3, FLAC, WAV, OGG, Opus or M4A file.')];

function replaceFile(f){
  const i=h('input',{type:'file',accept:'audio/*,.flac,.opus,.m4a'});
  i.onchange=()=>{if(!i.files[0])return;const fd=new FormData();fd.append('file',i.files[0]);act(()=>api(`/files/${f.id}/content`,{method:'PUT',body:fd}),'File replaced. Players will download the new version.')};
  i.click();
}

function upload(){
  const d=$('#dlg'),fIn=h('input',{type:'file',accept:'audio/*,.flac,.opus,.m4a'}),tIn=h('input',{placeholder:'Defaults to the file name'}),err=h('p',{class:'err'});
  d.replaceChildren(h('h2',{},'Upload audio'),h('label',{},'Audio file'),fIn,h('label',{},'Title'),tIn,err,
    h('div',{class:'foot'},h('button',{class:'ghost',onclick:()=>d.close()},'Cancel'),
      h('button',{class:'btn',onclick:async e=>{if(!fIn.files[0]){err.textContent='Choose an audio file.';return}
        e.target.disabled=true;err.textContent='Uploading…';
        try{const fd=new FormData();fd.append('file',fIn.files[0]);fd.append('title',tIn.value);await api('/files',{method:'POST',body:fd});d.close();toast('Uploaded');await load()}
        catch(x){err.textContent=x.message;e.target.disabled=false}}},'Upload')));
  d.showModal();
}

function assign({uid='',label='',file_id=''}){
  const d=$('#dlg');let mode=S.files.length?'pick':'new';
  const uidIn=h('input',{class:'mono',placeholder:'e.g. 04A1B2C3D4',value:uid,...(uid?{readonly:''}:{})});
  const labelIn=h('input',{placeholder:'Optional, e.g. Bedtime story',value:label});
  const sel=h('select',{},S.files.map(f=>h('option',{value:f.id,...(f.id==file_id?{selected:''}:{})},f.title)));
  const prev=h('audio',{controls:'',preload:'none'});
  const setPrev=()=>{if(sel.value)prev.src=`/api/v1/files/${sel.value}/download`};sel.onchange=setPrev;setPrev();
  const fIn=h('input',{type:'file',accept:'audio/*,.flac,.opus,.m4a'}),tIn=h('input',{placeholder:'Title (defaults to the file name)'});
  const pickBox=h('div',{},h('label',{},'Audio'),sel,prev),newBox=h('div',{},h('label',{},'Audio file'),fIn,h('label',{},'Title'),tIn);
  const err=h('p',{class:'err'});
  const bPick=h('button',{onclick:()=>set('pick')},'Use existing audio'),bNew=h('button',{onclick:()=>set('new')},'Upload new');
  const set=m=>{mode=m;bPick.className=m==='pick'?'on':'';bNew.className=m==='new'?'on':'';pickBox.hidden=m!=='pick';newBox.hidden=m!=='new';err.textContent=''};
  d.replaceChildren(h('h2',{},uid?'Assign audio to '+uid:'Add a card'),
    ...(uid?[]:[h('label',{},'Card ID'),uidIn]),
    h('label',{},'Name'),labelIn,
    ...(S.files.length?[h('div',{class:'seg'},bPick,bNew)]:[]),pickBox,newBox,err,
    h('div',{class:'foot'},h('button',{class:'ghost',onclick:()=>d.close()},'Cancel'),
      h('button',{class:'btn',onclick:async e=>{
        try{const id0=uidIn.value.trim();if(!id0)throw new Error('Enter the card ID.');let fid=sel.value;
          e.target.disabled=true;
          if(mode==='new'){if(!fIn.files[0])throw new Error('Choose an audio file.');const fd=new FormData();fd.append('file',fIn.files[0]);fd.append('title',tIn.value);fid=(await api('/files',{method:'POST',body:fd})).id}
          if(!fid)throw new Error('Choose an audio file.');
          await api('/mappings/'+encodeURIComponent(id0),json('PUT',{file_id:+fid,label:labelIn.value}));
          d.close();toast('Card assigned');await load()}
        catch(x){err.textContent=x.message;e.target.disabled=false}}},'Assign audio')));
  set(mode);d.showModal();
}

// Pick up new scans without a reload while the Waiting tab is open.
setInterval(()=>{if(S.tab!=='waiting'||$('#dlg').open)return;
  api('/failed').then(f=>{if(JSON.stringify(f)!==JSON.stringify(S.failed)){S.failed=f;render()}}).catch(()=>{})},4000);
load().catch(e=>toast(e.message,1));
