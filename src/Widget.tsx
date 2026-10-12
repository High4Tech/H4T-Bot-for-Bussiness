import {Button as ShadButton} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {Checkbox} from '@/components/ui/checkbox';
import {Card,CardContent,CardFooter,CardHeader} from '@/components/ui/card';
import {Avatar,AvatarImage,AvatarFallback} from '@/components/ui/avatar';
import {Badge} from '@/components/ui/badge';
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
  return <Card className={config.dark?'dark flex h-full min-h-[31rem] w-full flex-col gap-0 overflow-hidden rounded-2xl shadow-lg':'flex h-full min-h-[31rem] w-full flex-col gap-0 overflow-hidden rounded-2xl shadow-lg'} style={{'--primary':config.color,'--primary-foreground':accentText,'--ring':config.color} as CSSProperties} aria-label={config.name+' chat'}>
    <CardHeader className="flex flex-row items-center gap-3 bg-primary px-4 py-4 text-primary-foreground">
      <Avatar className="size-10 border border-white/40 bg-white"><AvatarImage src={config.avatar}/><AvatarFallback>{config.botName.slice(0,1)}</AvatarFallback></Avatar>
      <div className="min-w-0 flex-1"><strong className="block truncate text-sm">{config.botName}</strong><span className="block truncate text-xs opacity-80">{config.name} · {requested?'Local handoff queue':aiReady?'Knowledge-backed assistant':'Local preview'}</span></div>
      {(onClose||window.parent!==window)&&<ShadButton size="icon" variant="ghost" className="text-current hover:bg-white/15 hover:text-current" aria-label="Close chat" onClick={close}><Icon name="close"/></ShadButton>}
    </CardHeader>
    <CardContent className="flex min-h-0 flex-1 flex-col p-0">
      <div className="border-b px-4 py-2 text-center text-xs text-muted-foreground">{isFixture(company)?'Scripted sample assistant':aiReady?'Local AI · answers cite published sources':'Local AI setup needed · handoff is available'}</div>
      {error&&<p className="m-3 rounded-lg border border-destructive/30 p-2 text-xs text-destructive" role="alert">{error}</p>}
      {stage==='home'&&<div className="flex flex-1 flex-col gap-5 overflow-auto p-6"><div><Badge variant="secondary">Here to help</Badge><h2 className="mt-4 text-2xl font-semibold tracking-tight">{config.welcome}</h2><p className="mt-2 text-sm text-muted-foreground">{config.description}</p></div><div className="mt-auto grid gap-2">{config.questions.map(q=><ShadButton variant="outline" className="h-auto justify-between whitespace-normal py-3 text-left" key={q} disabled={busy} onClick={()=>void begin(q)}><span>{q}</span><Icon name="arrow"/></ShadButton>)}</div><Button variant="primary" disabled={busy} onClick={()=>void begin()}>Start a conversation <Icon name="arrow"/></Button><small className="text-xs text-muted-foreground">{isFixture(company)?'Sample conversation only.':'Conversations are saved in this business’s local workspace.'}</small></div>}
      {stage==='lead'&&<form className="grid flex-1 content-start gap-4 overflow-auto p-6" onSubmit={leadSubmit}><h2 className="text-xl font-semibold">A quick introduction</h2><p className="text-sm text-muted-foreground">Share contact details with this business before starting a chat.</p><Field label="Your name" required maxLength={80} value={leadName} onChange={e=>setLeadName(e.target.value)}/><Field label="Email address" type="email" required maxLength={150} value={leadEmail} onChange={e=>setLeadEmail(e.target.value)}/><Label className="flex items-center gap-2 text-sm"><Checkbox required/>I agree to share these details with this business.</Label><Button type="submit" variant="primary">Continue to chat <Icon name="arrow"/></Button><Button type="button" variant="ghost" onClick={()=>setStage('home')}>Back</Button></form>}
      {stage==='chat'&&<><div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto p-4" role="log" aria-live="polite"><p className="self-center text-xs text-muted-foreground">Today</p><div className="w-fit max-w-[86%] whitespace-pre-wrap break-words rounded-xl border bg-muted px-3 py-2 text-sm">{config.welcome}</div>{conversation?.messages.map(m=><div key={m.id} className={m.role==='visitor'?'ml-auto w-fit max-w-[86%] whitespace-pre-wrap break-words rounded-xl bg-primary px-3 py-2 text-sm text-primary-foreground':'w-fit max-w-[86%] whitespace-pre-wrap break-words rounded-xl border bg-muted px-3 py-2 text-sm'}>{m.role==='agent'&&<small className="block text-xs text-muted-foreground">Team reply</small>}{m.text}{!!m.citations?.length&&<span className="mt-2 grid gap-1 border-t pt-2 text-xs"><strong>Sources</strong>{m.citations.map((c,i)=>c.url?<a className="underline" href={c.url} target="_blank" rel="noopener noreferrer" key={i}>{c.title}</a>:<span key={i}>{c.title}</span>)}</span>}</div>)}{busy&&<div className="text-xs text-muted-foreground" role="status">{aiReady?'Checking published sources':'Saving your message'}…</div>}<div ref={end}/></div>
      <div className="grid gap-2 border-t p-4">{requested?<div className="text-xs text-muted-foreground">Local handoff {conversation?.status==='HUMAN_ASSIGNED'?'assigned':'requested'}. Try replying in the local inbox.</div>:conversation?.status==='RESOLVED'?<div className="text-xs text-muted-foreground">Conversation resolved.<ShadButton variant="ghost" disabled={busy} onClick={()=>void begin()}>Start again</ShadButton></div>:<ShadButton variant="link" className="h-auto justify-start p-0 text-xs" onClick={()=>send('Talk to a person')}>Talk to a person <Icon name="arrow"/></ShadButton>}<form className="flex items-center gap-2" onSubmit={e=>{e.preventDefault();send(text);}}><Input aria-label="Your message" placeholder="Write your message…" maxLength={2000} value={text} disabled={conversation?.status==='RESOLVED'} onChange={e=>setText(e.target.value)}/><ShadButton size="icon" aria-label="Send message" disabled={busy||!text.trim()||conversation?.status==='RESOLVED'}><Icon name="send"/></ShadButton></form></div></>}
    </CardContent>
    <CardFooter className="flex items-center justify-between gap-2 border-t px-4 py-2 text-xs text-muted-foreground">{config.logo&&<img className="max-h-6 max-w-10 object-contain" src={config.logo} alt={config.name+' logo'}/>}<div>Powered by <strong>H4T Bot</strong></div><span>{aiReady?'Local AI':'Local preview'}</span></CardFooter>
  </Card>;
}
