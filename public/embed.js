/* Local UI demo only. No credentials, visitor DOM reading or remote services. */
(() => {
  const script=document.currentScript;
  if (!(script instanceof HTMLScriptElement)) return;
  const base=new URL(script.src).origin;
  // Until a backend enforces approved host origins, allow loopback demo sites only.
  if (!['localhost','127.0.0.1','[::1]'].includes(location.hostname)) return;
  const candidate=script.dataset.botId||'high4tech';
  if(!/^(high4tech|cedar|[a-f0-9]{32})$/.test(candidate))return;
  const bot=candidate;
  const isCedar=bot==='cedar';
  let position=isCedar?'left':'right';
  const launcher=document.createElement('button');
  launcher.type='button';
  launcher.textContent='Chat with '+(isCedar?'Cedar':'High4Tech')+' ↗';
  launcher.setAttribute('aria-label','Open demo chat');
  launcher.setAttribute('aria-expanded','false');
  Object.assign(launcher.style,{position:'fixed',bottom:'24px',[isCedar?'left':'right']:'24px',zIndex:'2147483000',background:isCedar?'#28745B':'#F97328',color:isCedar?'white':'#241c17',border:'0',borderRadius:'100px',padding:'16px 24px',font:'600 14px system-ui',boxShadow:'0 6px 24px #0002',cursor:'pointer'});
  const frame=document.createElement('iframe');
  frame.title='Company chat · Local demo';
  frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-forms');
  frame.src=base+'/widget?company='+bot;
  frame.hidden=true;
  function geometry(){const mobile=innerWidth<600;Object.assign(frame.style,{position:'fixed',zIndex:'2147483001',border:'0',borderRadius:'14px',boxShadow:'0 16px 60px #0003',width:mobile?'calc(100vw - 24px)':'390px',height:mobile?'calc(100dvh - 24px)':'min(620px, calc(100dvh - 48px))',bottom:mobile?'12px':'24px',left:mobile||position==='left'?(mobile?'12px':'24px'):'auto',right:!mobile&&position==='right'?'24px':'auto'});}
  geometry();window.addEventListener('resize',geometry);
  function close(){frame.hidden=true;launcher.hidden=false;launcher.setAttribute('aria-expanded','false');launcher.focus();}
  launcher.addEventListener('click',()=>{frame.hidden=false;launcher.hidden=true;launcher.setAttribute('aria-expanded','true');frame.focus();});
  window.addEventListener('message',event=>{
    if(event.origin!==base||event.source!==frame.contentWindow)return;
    const d=event.data;
    if(d?.type==='h4t-close')close();
    if(d?.type==='h4t-appearance'&&typeof d.name==='string'&&d.name.length<=80&&/^#[0-9a-f]{6}$/i.test(d.color)&&['left','right'].includes(d.position)&&['#171717','#ffffff'].includes(d.textColor)){
      position=d.position;launcher.textContent='Chat with '+d.name+' ↗';
      Object.assign(launcher.style,{background:d.color,color:d.textColor,left:position==='left'?'24px':'auto',right:position==='right'?'24px':'auto'});geometry();
    }
  });
  window.addEventListener('keydown',event=>{if(event.key==='Escape'&&!frame.hidden)close();});
  document.body.append(launcher,frame);
})();
