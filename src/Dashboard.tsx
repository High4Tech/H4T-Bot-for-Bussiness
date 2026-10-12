import {Input} from '@/components/ui/input';
import {Textarea} from '@/components/ui/textarea';
import {Label} from '@/components/ui/label';
import {Checkbox} from '@/components/ui/checkbox';
import {NativeSelect,NativeSelectOption} from '@/components/ui/native-select';
import {useEffect,useState} from 'react';
import Widget from './Widget';
import DashboardShell from './DashboardShell';
import Channels from './Channels';
import Knowledge from './Knowledge';
import Assistant from './Assistant';
import {useAuth} from './Auth';
import {type BotConfig} from './demo-model.mjs';
import {saveConfig,useCompany,refreshWorkspace,savePlan} from './store';
import {Badge,Button,Field,Icon} from './ui';
import {GoOverview,GoChats} from './GoData';
import {GoSettings,GoTeam} from './GoSettings';
import {Card,CardContent,CardDescription,CardFooter,CardHeader,CardTitle} from '@/components/ui/card';
import {Progress} from '@/components/ui/progress';

const titles:Record<string,[string,string]>={
  overview:['Dashboard','A clear view of your saved customer conversations.'],
  assistant:['Your assistant','Shape the welcome your customers receive.'],
  inbox:['Chats','Read conversations, handle handoffs and follow up with visitors.'],
  knowledge:['Knowledge','Publish a source, wait for Ready, then ask your assistant about it.'],
  appearance:['Appearance','Shape the welcome your customers receive.'],
  channels:['Integrations','One assistant, with the same knowledge and brand across every channel.'],
  billing:['Pricing','Explore proposed plans. All amounts and subscriptions are Demo.'],
  team:['Users','Prepare your local team directory. Invitations and team sign-in come later.'],
  settings:['Settings','Save business hours and assistant preferences as local drafts.'],
};
export default function Dashboard(){
  const {user,logout}=useAuth();
  const company=user!.botId!;
  const [ready,setReady]=useState(false);
  const [loadError,setLoadError]=useState('');
  useEffect(()=>{
    let live=true;let polling=false;
    async function sync(){if(polling||document.hidden)return;polling=true;try{await refreshWorkspace(company);if(live){setReady(true);setLoadError('');}}catch(e){if(live)setLoadError((e as Error).message);}finally{polling=false;}}
    void sync();const interval=setInterval(()=>void sync(),2500);return()=>{live=false;clearInterval(interval);};
  },[company]);
  const data=useCompany(company);
  const [page,setPage]=useState(location.hash.slice(2)||'overview');
  const [dark,setDark]=useState(false);
  const [testOpen,setTestOpen]=useState(false);
  const [focusChat,setFocusChat]=useState('');
  useEffect(()=>{const fn=()=>setPage(location.hash.slice(2)||'overview');window.addEventListener('hashchange',fn);return()=>window.removeEventListener('hashchange',fn);},[]);
  const alias=page==='install'?'channels':page==='bots'?'assistant':page;
  const active=alias in titles?alias:'overview';
  function go(id:string){location.hash='/'+id;setPage(id);}
  function viewChat(id:string){setFocusChat(id);go('inbox');}
  function searchWorkspace(){go('inbox');setTimeout(()=>document.querySelector<HTMLInputElement>('input[aria-label="Search conversations"]')?.focus(),0);}
  useEffect(()=>{function shortcut(event:KeyboardEvent){if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();searchWorkspace();}}window.addEventListener('keydown',shortcut);return()=>window.removeEventListener('keydown',shortcut);});
  if(!ready)return <div className="p-12 text-sm text-muted-foreground">{loadError||'Opening your business workspace…'}</div>;
  return <DashboardShell company={company} business={data.config.name} active={active} title={titles[active][0]} description={titles[active][1]} user={user!} waiting={data.conversations.filter(c=>c.status==='HUMAN_REQUESTED').length} dark={dark} onDark={()=>setDark(!dark)} onSignOut={()=>void logout().catch(e=>setLoadError(e.message))} onSearch={searchWorkspace} onPreview={()=>setTestOpen(true)} previewOpen={testOpen} onPreviewOpen={setTestOpen} onNavigate={go} error={loadError}>
    {active==='overview'&&<GoOverview company={company} onView={viewChat}/>}
    {active==='assistant'&&<Assistant company={company} go={go} onPreview={()=>setTestOpen(true)} connectionError={loadError}/>}
    {active==='inbox'&&<GoChats key={company} company={company} initialId={focusChat}/>}
    {active==='knowledge'&&<Knowledge key={company} company={company}/>}
    {active==='appearance'&&<Appearance key={company} company={company}/>}
    {active==='channels'&&<Channels company={company}/>}
    {active==='billing'&&<Billing key={company} company={company}/>}
    {active==='settings'&&<GoSettings company={company}/>}
    {active==='team'&&<GoTeam company={company}/>}
  </DashboardShell>;
}

function Appearance({company}:{company:string}){
  const data=useCompany(company);
  const [draft,setDraft]=useState<BotConfig>({...data.config});
  const [notice,setNotice]=useState('');
  function update<K extends keyof BotConfig>(key:K,value:BotConfig[K]){setDraft(d=>({...d,[key]:value}));setNotice('');}
  function upload(file:File|undefined,key:'avatar'|'logo'){
    if(!file)return;
    if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>500000){setNotice('Use a PNG, JPG or WebP image under 500 KB.');return;}
    const reader=new FileReader();reader.onload=()=>update(key,String(reader.result));reader.readAsDataURL(file);
  }
  return <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(20rem,1fr)]">
    <Card>
      <form onSubmit={async e=>{e.preventDefault();try{await saveConfig(company,draft);setNotice('Appearance saved to your local workspace.');}catch(e){setNotice((e as Error).message);}}}>
        <CardHeader className="flex flex-row items-start justify-between gap-3"><div><CardTitle>Brand & welcome</CardTitle><CardDescription>Your widget, your voice.</CardDescription></div><Badge>Draft preview</Badge></CardHeader>
        <CardContent className="grid gap-5">
          <Field label="Business name" required maxLength={80} value={draft.name} onChange={e=>update('name',e.target.value)}/>
          <Field label="Assistant name" required maxLength={80} value={draft.botName} onChange={e=>update('botName',e.target.value)}/>
          <div className="grid gap-4 sm:grid-cols-2">
            <Label className="grid gap-2 text-sm">Accent color<Input aria-label="Accent color" type="color" className="h-10 w-full p-1" value={draft.color} onChange={e=>update('color',e.target.value)}/></Label>
            <Label className="grid gap-2 text-sm">Launcher position<NativeSelect className="w-full" value={draft.position} onChange={e=>update('position',e.target.value)}><NativeSelectOption value="right">Bottom right</NativeSelectOption><NativeSelectOption value="left">Bottom left</NativeSelectOption></NativeSelect></Label>
          </div>
          <Field label="Welcome message" required maxLength={180} value={draft.welcome} onChange={e=>update('welcome',e.target.value)}/>
          <Field label="Short description" maxLength={180} value={draft.description} onChange={e=>update('description',e.target.value)}/>
          <Label className="grid gap-2 text-sm">Suggested questions<Textarea value={draft.questions.join('\n')} maxLength={300} onChange={e=>update('questions',e.target.value.split('\n').slice(0,3))}/><small className="font-normal">One per line, up to three.</small></Label>
          <div className="grid gap-4 sm:grid-cols-2"><Label className="grid gap-2 text-sm">Company logo<Input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload(e.target.files?.[0],'logo')}/></Label><Label className="grid gap-2 text-sm">Assistant avatar<Input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload(e.target.files?.[0],'avatar')}/></Label></div>
          <Label className="flex items-center gap-2 text-sm"><Checkbox checked={draft.leadForm} onCheckedChange={v=>update('leadForm',v===true)}/>Ask for name and email before chat</Label>
          <Label className="flex items-center gap-2 text-sm"><Checkbox checked={draft.dark} onCheckedChange={v=>update('dark',v===true)}/>Use dark widget theme</Label>
        </CardContent>
        <CardFooter className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t pt-5"><span className="text-xs text-muted-foreground" role="status">{notice||'Changes appear in the preview.'}</span><Button variant="primary">Save appearance</Button></CardFooter>
      </form>
    </Card>
    <div className="flex flex-col items-center gap-4 rounded-xl bg-muted p-5"><div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Live appearance preview</div><div className="h-[34rem] w-full max-w-sm"><Widget key={company} company={company} previewConfig={draft}/></div><p className="text-center text-xs text-muted-foreground">Your preview uses local knowledge-backed replies once sources are Ready.<br/>Appearance is saved to this PC’s local service.</p></div>
  </div>;
}
function Billing({company}:{company:string}){
  const data=useCompany(company);const selected=data.billing?.plan||'Starter';
  const [pending,setPending]=useState('');const [requestId,setRequestId]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
  const allowance=selected==='Starter'?100:selected==='Growth'?500:2000;
  const plans=[['Starter','19','1 assistant · 1 agent seat','100 proposed answers'],['Growth','49','1 assistant · 3 agent seats','500 proposed answers'],['Business','149','1 assistant · 10 agent seats','2,000 proposed answers']];
  return <div className="space-y-5">
    <Card><CardHeader><Badge>Demo subscription</Badge><CardTitle>{selected} plan</CardTitle><CardDescription>No payment has been collected.</CardDescription></CardHeader><CardContent><div className="mb-3 flex items-end gap-2"><strong className="text-3xl tabular-nums">{data.billing?.aiAnswers??0}</strong><span className="pb-1 text-sm text-muted-foreground">/ {allowance} local AI answers</span></div><Progress value={Math.min(100,100*(data.billing?.aiAnswers??0)/allowance)}/><p className="mt-2 text-xs text-muted-foreground">Proposed Demo allowance</p></CardContent></Card>
    <div className="grid gap-4 lg:grid-cols-3">{plans.map(([name,price,seats,answers])=><Card key={name} className={selected===name?'border-primary':''}><CardHeader><Badge>{selected===name?'Current demo plan':'Demo plan'}</Badge><CardTitle>{name}</CardTitle><CardDescription><strong className="text-3xl text-foreground">${price}</strong> / month</CardDescription></CardHeader><CardContent className="grid gap-2 text-sm"><p>{seats}</p><p>{answers}</p><small>Proposed allowances, subject to benchmarking.</small></CardContent><CardFooter><Button disabled={selected===name} variant={name==='Growth'?'primary':'secondary'} onClick={()=>{setPending(name);setRequestId(crypto.randomUUID());setNotice('');}}>{selected===name?'Selected':'Try demo '+name}</Button></CardFooter></Card>)}</div>
    {pending&&<Card><CardHeader><CardTitle>Demo checkout · {pending}</CardTitle><CardDescription>This changes only the local plan preview. No card details or payment are needed.</CardDescription></CardHeader><CardFooter className="flex gap-2"><Button variant="primary" disabled={busy} onClick={async()=>{setBusy(true);try{await savePlan(company,pending,requestId);setPending('');setNotice('Demo plan and invoice saved locally. No payment collected.');}catch(e){setNotice((e as Error).message);}finally{setBusy(false);}}}>Confirm demo plan</Button><Button onClick={()=>setPending('')}>Cancel</Button></CardFooter></Card>}
    <Card><CardHeader className="flex flex-row items-start justify-between"><div><CardTitle>Demo invoices</CardTitle><CardDescription role="status">{notice||'Saved Demo invoices. No payment has been collected.'}</CardDescription></div><Badge>Simulated</Badge></CardHeader><CardContent className="grid gap-2">{data.billing?.invoices.length?data.billing.invoices.map(invoice=><div className="flex items-center justify-between gap-4 rounded-lg border p-3 text-sm" key={invoice.id}><div><strong>{invoice.plan} · Demo invoice</strong><p>{new Date(invoice.created*1000).toLocaleDateString()} · {invoice.status}</p></div><strong>${(invoice.cents/100).toFixed(2)}</strong></div>):<p>No Demo invoices yet.</p>}</CardContent></Card>
  </div>;
}
