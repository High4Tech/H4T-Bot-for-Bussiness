import {useEffect,useState} from 'react';
import Widget from './Widget';
import Channels from './Channels';
import Knowledge from './Knowledge';
import Assistant from './Assistant';
import {useAuth} from './Auth';
import {type BotConfig} from './demo-model.mjs';
import {saveConfig,useCompany,refreshWorkspace,savePlan} from './store';
import {Badge,Brand,Button,Field,Icon} from './ui';
import {GoOverview,GoChats} from './GoData';
import {GoSettings,GoTeam} from './GoSettings';
const pages=[['overview','Dashboard'],['inbox','Chat record'],['knowledge','Knowledge'],['channels','Integrations'],['team','Users'],['settings','Settings'],['appearance','Appearance'],['billing','Pricing'],['assistant','Your assistant']];
const titles:Record<string,[string,string]>={
  overview:['Dashboard','A clear view of your saved customer conversations.'],
  assistant:['One assistant. Entirely yours.','Shape the welcome your customers receive.'],
  inbox:['Chats','Read conversations, handle handoffs and follow up with visitors.'],
  knowledge:['Knowledge','Publish a source, wait for Ready, then ask your assistant about it.'],
  appearance:['Make it yours','Shape the welcome your customers receive.'],
  channels:['Meet your customers where they are.','One assistant, with the same knowledge and brand across every channel.'],
  billing:['Pricing','Explore proposed plans. All amounts and subscriptions are Demo.'],
  team:['Users','Prepare your local team directory. Invitations and team sign-in come later.'],
  settings:['Settings','Save business hours and assistant preferences as local drafts.']
};
export default function Dashboard(){
  const {user,logout}=useAuth();
  const company=user!.botId!;
  const [ready,setReady]=useState(false);const [loadError,setLoadError]=useState('');
  useEffect(()=>{
    let live=true;let polling=false;
    async function sync(){if(polling||document.hidden)return;polling=true;try{await refreshWorkspace(company);if(live){setReady(true);setLoadError('');}}catch(e){if(live)setLoadError((e as Error).message);}finally{polling=false;}}
    void sync();const interval=setInterval(()=>void sync(),2500);return()=>{live=false;clearInterval(interval);};
  },[company]);
  const data=useCompany(company);
  const [page,setPage]=useState(location.hash.slice(2)||'overview');
  const [dark,setDark]=useState(false);
  const [navOpen,setNavOpen]=useState(false);
  const [testOpen,setTestOpen]=useState(false);
  const [focusChat,setFocusChat]=useState('');
  useEffect(()=>{if(!navOpen&&!testOpen)return;const close=(event:KeyboardEvent)=>{if(event.key==='Escape'){setNavOpen(false);setTestOpen(false);}};window.addEventListener('keydown',close);return()=>window.removeEventListener('keydown',close);},[navOpen,testOpen]);
  useEffect(()=>{const fn=()=>setPage(location.hash.slice(2)||'overview');window.addEventListener('hashchange',fn);return()=>window.removeEventListener('hashchange',fn);},[]);
  const alias=page==='install'?'channels':page==='bots'?'assistant':page;
  const active=alias in titles?alias:'overview';
  function go(id:string){location.hash='/'+id;setPage(id);setNavOpen(false);}
  function viewChat(id:string){setFocusChat(id);go('inbox');}
  function searchWorkspace(){go('inbox');setTimeout(()=>document.querySelector<HTMLInputElement>('input[aria-label="Search conversations"]')?.focus(),0);}
  useEffect(()=>{function shortcut(event:KeyboardEvent){if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();searchWorkspace();}}window.addEventListener('keydown',shortcut);return()=>window.removeEventListener('keydown',shortcut);});
  if(!ready)return <div className="loading-page">{loadError||'Opening your business workspace…'}</div>;
  return <div className={'dashboard go-dashboard '+(dark?'dark':'')}>
    {navOpen&&<button className="nav-scrim" aria-label="Close navigation" onClick={()=>setNavOpen(false)}/>}<aside id="workspace-navigation" className={'sidebar '+(navOpen?'nav-open':'')}><Brand/><button className="go-side-search" onClick={searchWorkspace}><Icon name="search"/><span>Search workspace</span><kbd>Ctrl K</kbd></button><div className="go-side-group">Workspace</div><nav aria-label="Workspace">{pages.slice(0,1).map(([id,label])=><a href={'#/'+id} key={id} className={active===id?'selected':''} aria-current={active===id?'page':undefined} onClick={()=>setNavOpen(false)}><Icon name={id}/><span>{label}</span></a>)}<div className="go-side-group">Conversations</div>{pages.slice(1,2).map(([id,label])=><a href={'#/'+id} key={id} className={active===id?'selected':''} aria-current={active===id?'page':undefined} onClick={()=>setNavOpen(false)}><Icon name={id}/><span>{label}</span>{data.conversations.some(c=>c.status==='HUMAN_REQUESTED')&&<span className="nav-count">{data.conversations.filter(c=>c.status==='HUMAN_REQUESTED').length}</span>}</a>)}<div className="go-side-group">Assistant</div>{pages.slice(2,7).map(([id,label])=><a href={'#/'+id} key={id} className={active===id?'selected':''} aria-current={active===id?'page':undefined} onClick={()=>setNavOpen(false)}><Icon name={id}/><span>{label}</span></a>)}</nav><div className="sidebar-bottom"><button className="go-upgrade" onClick={()=>go('knowledge')}><span className="go-upgrade-mark"><Icon name="knowledge"/></span><strong>Ground every answer</strong><small>Publish your website or files to answer with sources.</small><span className="go-upgrade-link">Open knowledge</span></button><button className="go-try" onClick={()=>setTestOpen(true)}><Icon name="eye"/> Try in browser <Icon name="arrow"/></button><div className="account"><span className="initials">{user!.name[0]}</span><div><strong>{user!.name}</strong><small>{user!.email}</small></div><button className="theme-button" aria-label="Sign out" onClick={()=>logout().catch(e=>setLoadError(e.message))}><Icon name="logout"/></button></div></div></aside>
    <div className="dashboard-main"><header className="topbar"><div className="breadcrumb"><button className="menu-button" aria-label="Toggle navigation" aria-expanded={navOpen} aria-controls="workspace-navigation" onClick={()=>setNavOpen(!navOpen)}><Icon name="menu"/></button>{data.config.name}<span>/</span><strong>{pages.find(p=>p[0]===active)?.[1]}</strong></div><div className="top-actions"><Badge tone={loadError?'warning':'success'}>{!loadError&&<span className="local-dot"/>}{loadError?'Connection interrupted':'Local workspace'}</Badge><button className="theme-button" onClick={()=>setDark(!dark)} aria-label={dark?'Switch to light mode':'Switch to dark mode'}><Icon name={dark?'sun':'moon'}/></button><span className="initials small">{user!.name[0]}</span></div></header>
    <main><div className="page-heading"><div><h1>{titles[active][0]}</h1><p>{titles[active][1]}</p></div><Button variant="primary" onClick={()=>setTestOpen(true)}><Icon name="eye"/>Try in browser <Icon name="arrow"/></Button></div><div className="demo-notice"><span><Icon name="sparkle"/></span><strong>Local preview</strong><span>Saved on this PC. Published, Ready knowledge powers local AI replies; billing is Demo.</span></div>
    {loadError&&<p className="inline-notice" role="alert">{loadError}</p>}
    {active==='overview'&&<GoOverview company={company} onView={viewChat}/>}
    {active==='assistant'&&<Assistant company={company} go={go} onPreview={()=>setTestOpen(true)} connectionError={loadError}/>}
    {active==='inbox'&&<GoChats key={company} company={company} initialId={focusChat}/>}
    {active==='knowledge'&&<Knowledge key={company} company={company}/>}
    {active==='appearance'&&<Appearance key={company} company={company}/>}
    {active==='channels'&&<Channels company={company}/>}
    {active==='billing'&&<Billing key={company} company={company}/>}
    {active==='settings'&&<GoSettings company={company}/>}
    {active==='team'&&<GoTeam company={company}/>}
    <footer className="dashboard-footer"><span>H4T Bot by High4Tech</span><span>Local prototype · No cloud services</span></footer>
    </main></div>
    {testOpen&&<div className="test-overlay"><button className="test-backdrop" aria-label="Close widget preview" onClick={()=>setTestOpen(false)}/><div className="test-widget"><Widget key={company} company={company} onClose={()=>setTestOpen(false)}/></div></div>}
  </div>;
}
function Appearance({company}:{company:string}){
  const data=useCompany(company);const [draft,setDraft]=useState<BotConfig>({...data.config});const [notice,setNotice]=useState('');
  function update<K extends keyof BotConfig>(key:K,value:BotConfig[K]){setDraft(d=>({...d,[key]:value}));setNotice('');}
  function upload(file:File|undefined,key:'avatar'|'logo'){if(!file)return;if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>500000){setNotice('Use a PNG, JPG or WebP image under 500 KB.');return;}const reader=new FileReader();reader.onload=()=>update(key,String(reader.result));reader.readAsDataURL(file);}
  return <div className="appearance-grid"><form className="panel appearance-form" onSubmit={async e=>{e.preventDefault();try{await saveConfig(company,draft);setNotice('Appearance saved to your local workspace.');}catch(e){setNotice((e as Error).message);}}}><div className="section-heading"><div><h2>Brand & welcome</h2><p>Your widget, your voice.</p></div><Badge>Draft preview</Badge></div><div className="form-body"><Field label="Business name" required maxLength={80} value={draft.name} onChange={e=>update('name',e.target.value)}/><Field label="Assistant name" required maxLength={80} value={draft.botName} onChange={e=>update('botName',e.target.value)}/><div className="two-fields"><label className="field"><span>Accent color</span><input aria-label="Accent color" type="color" value={draft.color} onChange={e=>update('color',e.target.value)}/></label><label className="field">Launcher position<select value={draft.position} onChange={e=>update('position',e.target.value)}><option value="right">Bottom right</option><option value="left">Bottom left</option></select></label></div><Field label="Welcome message" required maxLength={180} value={draft.welcome} onChange={e=>update('welcome',e.target.value)}/><Field label="Short description" maxLength={180} value={draft.description} onChange={e=>update('description',e.target.value)}/><label className="field">Suggested questions<textarea value={draft.questions.join('\n')} maxLength={300} onChange={e=>update('questions',e.target.value.split('\n').slice(0,3))}/><small>One per line, up to three.</small></label><div className="two-fields"><label className="field">Company logo<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload(e.target.files?.[0],'logo')}/></label><label className="field">Assistant avatar<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload(e.target.files?.[0],'avatar')}/></label></div><label className="check"><input type="checkbox" checked={draft.leadForm} onChange={e=>update('leadForm',e.target.checked)}/>Ask for name and email before chat</label><label className="check"><input type="checkbox" checked={draft.dark} onChange={e=>update('dark',e.target.checked)}/>Use dark widget theme</label></div><div className="form-footer"><span role="status">{notice||'Changes appear in the preview.'}</span><Button variant="primary">Save appearance</Button></div></form><div className="appearance-preview"><div className="preview-caption"><span className="local-dot"/>LIVE APPEARANCE PREVIEW</div><Widget key={company} company={company} previewConfig={draft}/><p>Your preview uses local knowledge-backed replies once sources are Ready.<br/>Appearance is saved to this PC’s local service.</p></div></div>;
}
function Billing({company}:{company:string}){
  const data=useCompany(company);const selected=data.billing?.plan||'Starter';const [pending,setPending]=useState('');const [requestId,setRequestId]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
  return <><section className="panel usage-panel"><div><Badge>Demo subscription</Badge><h2>{selected} plan</h2><p>No payment has been collected.</p></div><div><strong>{data.billing?.aiAnswers??0} <span>/ {selected==='Starter'?100:selected==='Growth'?500:2000}</span></strong><p>Local AI answers · proposed Demo allowance</p><div className="progress-track"/></div></section><div className="plans">{[['Starter','19','1 assistant · 1 agent seat','100 proposed answers'],['Growth','49','1 assistant · 3 agent seats','500 proposed answers'],['Business','149','1 assistant · 10 agent seats','2,000 proposed answers']].map(([name,price,bots,answers])=><section className={'panel plan '+(selected===name?'current':'')} key={name}><Badge>{selected===name?'Current demo plan':'Demo plan'}</Badge><h2>{name}</h2><p className="price"><strong>${price}</strong> / month</p><p>{bots}</p><p>{answers}</p><small>Proposed allowances, subject to benchmarking.</small><Button disabled={selected===name} variant={name==='Growth'?'primary':'secondary'} onClick={()=>{setPending(name);setRequestId(crypto.randomUUID());setNotice('');}}>{selected===name?'Selected':'Try demo '+name}</Button></section>)}</div>{pending&&<div className="panel demo-checkout"><h2>Demo checkout · {pending}</h2><p>This changes only the local plan preview. No card details or payment are needed.</p><Button variant="primary" disabled={busy} onClick={async()=>{setBusy(true);try{await savePlan(company,pending,requestId);setPending('');setNotice('Demo plan and invoice saved locally. No payment collected.');}catch(e){setNotice((e as Error).message);}finally{setBusy(false);}}}>Confirm demo plan</Button><Button onClick={()=>setPending('')}>Cancel</Button></div>}<div className="panel section-heading"><div><h2>Demo invoices</h2><p role="status">{notice||'Saved Demo invoices. No payment has been collected.'}</p></div><Badge>Simulated</Badge></div>{data.billing?.invoices.map(invoice=><div className="panel section-heading" key={invoice.id}><div><strong>{invoice.plan} · Demo invoice</strong><p>{new Date(invoice.created*1000).toLocaleDateString()} · {invoice.status}</p></div><strong>${(invoice.cents/100).toFixed(2)}</strong></div>)}</>;
}
