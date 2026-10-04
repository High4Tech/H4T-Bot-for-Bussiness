import {useEffect,useRef,useState,type CSSProperties,type FormEvent} from 'react';
import {demoReply,type BotConfig} from './demo-model.mjs';
import {addMessage,changeStatus,currentConversation,startChat,useCompany,visitorSession} from './store';
import {Button,Field,Icon,Mascot} from './ui';
export default function Widget({company='high4tech',previewConfig,onClose}:{company?:string;previewConfig?:BotConfig;onClose?:()=>void}) {
  const data=useCompany(company);
  const config=previewConfig??data.config;
  const [stage,setStage]=useState<'home'|'lead'|'chat'>(visitorSession(company)?'chat':'home');
  const [chatId,setChatId]=useState(visitorSession(company));
  const [text,setText]=useState('');
  const [busy,setBusy]=useState(false);
  const [leadName,setLeadName]=useState('');
  const [leadEmail,setLeadEmail]=useState('');
  const [initialPrompt,setInitialPrompt]=useState('');
  const end=useRef<HTMLDivElement>(null);
  const timer=useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const conversation=data.conversations.find(c=>c.id===chatId);
  useEffect(()=>()=>{clearTimeout(timer.current);},[]);
  useEffect(()=>{end.current?.scrollIntoView({block:'nearest'});},[conversation?.messages.length,busy]);
  function begin(prompt='') {
    if(config.leadForm && stage==='home'){setInitialPrompt(prompt);setStage('lead');return;}
    const id=startChat(company,leadName||'Guest visitor',leadEmail);setChatId(id);setStage('chat');
    if(prompt) send(prompt,id);
  }
  function send(value:string,id=chatId) {
    const message=value.trim();if(!message || busy)return;
    const active=currentConversation(company,id);
    if(!active || active.status==='RESOLVED')return;
    addMessage(company,id,'visitor',message);setText('');
    if(active.status!=='BOT_ACTIVE')return;
    const result=demoReply(message);
    if(result.handoff){changeStatus(company,id,'HUMAN_REQUESTED');addMessage(company,id,'bot',result.text);return;}
    setBusy(true);
    timer.current=setTimeout(()=>{
      if(currentConversation(company,id)?.status==='BOT_ACTIVE')addMessage(company,id,'bot',result.text);
      setBusy(false);
    },650);
  }
  function leadSubmit(e:FormEvent) {e.preventDefault();const id=startChat(company,leadName,leadEmail);setChatId(id);setStage('chat');if(initialPrompt)send(initialPrompt,id);}
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
    <header className="widget-header"><div className="widget-avatar"><Mascot src={config.avatar}/></div><div><strong>{config.botName}</strong><small>{config.name} · {requested?'Demo handoff queue':'Local demo'}</small></div>{(onClose||window.parent!==window)&&<button className="widget-close" aria-label="Close chat" onClick={close}>×</button>}</header>
    <div className="widget-demo">Scripted preview · AI is not connected</div>
    {stage==='home'&&<div className="widget-home"><div><span className="eyebrow">HERE TO HELP</span><h2>{config.welcome}</h2><p>{config.description}</p></div><div className="welcome-actions">{config.questions.map(q=><button key={q} onClick={()=>begin(q)}><span>{q}</span><span aria-hidden>↗</span></button>)}</div><Button variant="primary" onClick={()=>begin()}>Start a conversation <span aria-hidden>→</span></Button><small>No real visitor data is needed for this demo.</small></div>}
    {stage==='lead'&&<form className="lead-form" onSubmit={leadSubmit}><h2>A quick introduction</h2><p>Use sample details to try the local contact form.</p><Field label="Your name" required maxLength={80} value={leadName} onChange={e=>setLeadName(e.target.value)}/><Field label="Email address" type="email" required maxLength={150} value={leadEmail} onChange={e=>setLeadEmail(e.target.value)}/><label className="check"><input type="checkbox" required/>I agree to share these sample details in the demo inbox.</label><Button type="submit" variant="primary">Continue to chat →</Button><Button type="button" variant="ghost" onClick={()=>setStage('home')}>Back</Button></form>}
    {stage==='chat'&&<><div className="widget-thread" role="log" aria-live="polite"><p className="thread-date">Today · Demo conversation</p><div className="bubble bot">{config.welcome}</div>{conversation?.messages.map(m=><div key={m.id} className={'bubble '+m.role}>{m.role==='agent'&&<small>Demo team reply</small>}{m.text}</div>)}{busy&&<div className="typing" role="status">Preparing demo response<span>•••</span></div>}<div ref={end}/></div>
    <div className="widget-bottom">{requested?<div className="handoff-note">Demo handoff {conversation?.status==='HUMAN_ASSIGNED'?'assigned':'requested'}. Try replying in the local inbox.</div>:conversation?.status==='RESOLVED'?<div className="handoff-note">Conversation resolved.<button onClick={()=>begin()}>Start again</button></div>:<button className="handoff-link" onClick={()=>send('Talk to a person')}>Talk to a person ↗</button>}<form className="composer" onSubmit={e=>{e.preventDefault();send(text);}}><input aria-label="Your message" placeholder="Write your message…" maxLength={2000} value={text} disabled={conversation?.status==='RESOLVED'} onChange={e=>setText(e.target.value)}/><button aria-label="Send message" disabled={busy||!text.trim()||conversation?.status==='RESOLVED'}><Icon name="send"/></button></form></div></>}
    <footer className="widget-footer">{config.logo&&<img className="widget-company-logo" src={config.logo} alt={config.name+' logo'}/>}<div>Powered by <strong>H4T Bot</strong></div><span>Local demo</span></footer>
  </section>;
}
