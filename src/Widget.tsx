import {useEffect,useRef,useState,type CSSProperties,type FormEvent} from 'react';
import {demoReply,type BotConfig} from './demo-model.mjs';
import {addMessage,changeStatus,currentConversation,startChat,useCompany,visitorSession,isFixture,refreshVisitor,clearVisitorSession} from './store';
import {Button,Field,Icon,Mascot} from './ui';
import {api} from './api';
export default function Widget({company='high4tech',previewConfig,onClose}:{company?:string;previewConfig?:BotConfig;onClose?:()=>void}) {
  const data=useCompany(company);
  const config=previewConfig??data.config;
  const [stage,setStage]=useState<'home'|'lead'|'chat'>(visitorSession(company)?'chat':'home');
  const [chatId,setChatId]=useState(visitorSession(company));
  const [text,setText]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [leadName,setLeadName]=useState('');
  const [leadEmail,setLeadEmail]=useState('');
  const [initialPrompt,setInitialPrompt]=useState('');
  const [aiReady,setAiReady]=useState(false);
  const end=useRef<HTMLDivElement>(null);
  const timer=useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const conversation=data.conversations.find(c=>c.id===chatId);
  useEffect(()=>()=>{clearTimeout(timer.current);},[]);
  useEffect(()=>{if(isFixture(company))return;let live=true;api<{mode:string}>('/engine/status').then(value=>{if(live)setAiReady(value.mode==='local-rag');}).catch(()=>{if(live)setAiReady(false);});return()=>{live=false;};},[company]);
  useEffect(()=>{end.current?.scrollIntoView({block:'nearest'});},[conversation?.messages.length,busy]);
  useEffect(()=>{
    if(!chatId||isFixture(company))return;
    let live=true;let polling=false;
    async function sync(){if(polling||document.hidden)return;polling=true;try{await refreshVisitor(company,chatId);if(live)setError('');}catch(e){if(live)setError((e as Error).message);}finally{polling=false;}}
    void sync();const interval=setInterval(()=>void sync(),2500);return()=>{live=false;clearInterval(interval);};
  },[company,chatId]);
  async function begin(prompt='') {
    if(busy)return;
    if(config.leadForm && stage==='home'){setInitialPrompt(prompt);setStage('lead');return;}
    setBusy(true);setError('');
    try{const id=await startChat(company,leadName||'Guest visitor',leadEmail);setChatId(id);setStage('chat');if(prompt)await deliver(prompt,id);}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function deliver(message:string,id:string){
    const active=currentConversation(company,id);if(!active||active.status==='RESOLVED')return;
    await addMessage(company,id,'visitor',message);setText('');
    if(!isFixture(company)||active.status!=='BOT_ACTIVE')return;
    const result=demoReply(message);
    if(result.handoff){await changeStatus(company,id,'HUMAN_REQUESTED');await addMessage(company,id,'bot',result.text);return;}
    await new Promise<void>(resolve=>{timer.current=setTimeout(()=>resolve(),650);});
    if(currentConversation(company,id)?.status==='BOT_ACTIVE')await addMessage(company,id,'bot',result.text);
  }
  async function send(value:string,id=chatId) {
    const message=value.trim();if(!message||busy)return;
    setBusy(true);setError('');try{await deliver(message,id);}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  function leadSubmit(e:FormEvent) {e.preventDefault();void begin(initialPrompt);}
  function close() {
    if(onClose)onClose();
    else if(window.parent!==window && document.referrer){
      const parent=new URL(document.referrer);
      if(['localhost','127.0.0.1','[::1]'].includes(parent.hostname))window.parent.postMessage({type:'h4t-close'},parent.origin);
    }
  }
  useEffect(()=>{const key=(event:KeyboardEvent)=>{if(event.key==='Escape')close();};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[onClose]);
  const requested=conversation?.status.startsWith('HUMAN');
  const hex=config.color.replace('#','');
  const rgb=[0,2,4].map(offset=>parseInt(hex.slice(offset,offset+2),16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);
  const luminance=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];
  const accentText=luminance>.179?'#171717':'#ffffff';
  useEffect(()=>{
    if(window.parent===window||!document.referrer)return;
    const parent=new URL(document.referrer);
    if(['localhost','127.0.0.1','[::1]'].includes(parent.hostname)){
      window.parent.postMessage({type:'h4t-appearance',name:config.name,color:config.color,position:config.position,textColor:accentText},parent.origin);
    }
  },[config.name,config.color,config.position,accentText]);
  return <section className={'widget '+(config.dark?'widget-dark':'')} style={{'--widget-accent':config.color,'--widget-accent-text':accentText} as CSSProperties} aria-label={config.name+' chat'}>
    <header className="widget-header"><div className="widget-avatar"><Mascot src={config.avatar}/></div><div><strong>{config.botName}</strong><small>{config.name} · {requested?'Local handoff queue':aiReady?'Knowledge-backed assistant':'Local preview'}</small></div>{(onClose||window.parent!==window)&&<button className="widget-close" aria-label="Close chat" onClick={close}>×</button>}</header>
    <div className="widget-demo">{isFixture(company)?'Scripted sample assistant':aiReady?'Local AI · answers cite published sources':'Local AI setup needed · handoff is available'}</div>
    {stage==='home'&&<div className="widget-home"><div><span className="eyebrow">Here to help</span><h2>{config.welcome}</h2><p>{config.description}</p></div><div className="welcome-actions">{config.questions.map(q=><button key={q} disabled={busy} onClick={()=>void begin(q)}><span>{q}</span><Icon name="arrow"/></button>)}</div><Button variant="primary" disabled={busy} onClick={()=>void begin()}>Start a conversation <Icon name="arrow"/></Button><small>{isFixture(company)?'Sample conversation only.':'Conversations are saved in this business’s local workspace.'}</small></div>}
    {stage==='lead'&&<form className="lead-form" onSubmit={leadSubmit}><h2>A quick introduction</h2><p>Share contact details with this business before starting a chat.</p><Field label="Your name" required maxLength={80} value={leadName} onChange={e=>setLeadName(e.target.value)}/><Field label="Email address" type="email" required maxLength={150} value={leadEmail} onChange={e=>setLeadEmail(e.target.value)}/><label className="check"><input type="checkbox" required/>I agree to share these details with this business.</label><Button type="submit" variant="primary">Continue to chat →</Button><Button type="button" variant="ghost" onClick={()=>setStage('home')}>Back</Button></form>}
    {stage==='chat'&&<><div className="widget-thread" role="log" aria-live="polite"><p className="thread-date">Today</p><div className="bubble bot">{config.welcome}</div>{conversation?.messages.map(m=><div key={m.id} className={'bubble '+m.role}>{m.role==='agent'&&<small>Team reply</small>}{m.text}{!!m.citations?.length&&<span className="widget-citations"><strong>Sources</strong>{m.citations.map((c,i)=>c.url?<a href={c.url} target="_blank" rel="noopener noreferrer" key={i}>{c.title}</a>:<span key={i}>{c.title}</span>)}</span>}</div>)}{busy&&<div className="typing" role="status">{aiReady?'Checking published sources':'Saving your message'}<span>•••</span></div>}<div ref={end}/></div>
    <div className="widget-bottom">{requested?<div className="handoff-note">Local handoff {conversation?.status==='HUMAN_ASSIGNED'?'assigned':'requested'}. Try replying in the local inbox.</div>:conversation?.status==='RESOLVED'?<div className="handoff-note">Conversation resolved.<button disabled={busy} onClick={()=>void begin()}>Start again</button></div>:<button className="handoff-link" onClick={()=>send('Talk to a person')}>Talk to a person ↗</button>}<form className="composer" onSubmit={e=>{e.preventDefault();send(text);}}><input aria-label="Your message" placeholder="Write your message…" maxLength={2000} value={text} disabled={conversation?.status==='RESOLVED'} onChange={e=>setText(e.target.value)}/><button aria-label="Send message" disabled={busy||!text.trim()||conversation?.status==='RESOLVED'}><Icon name="send"/></button></form></div></>}
    <footer className="widget-footer">{config.logo&&<img className="widget-company-logo" src={config.logo} alt={config.name+' logo'}/>}<div>Powered by <strong>H4T Bot</strong></div><span>{aiReady?'Local AI':'Local preview'}</span></footer>
  </section>;
}
