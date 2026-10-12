import {Avatar,AvatarFallback,AvatarImage} from '@/components/ui/avatar';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Card,CardContent,CardDescription,CardFooter,CardHeader,CardTitle} from '@/components/ui/card';
import {Separator} from '@/components/ui/separator';
import {useCompany} from './store';
import {Icon,Mascot} from './ui';

type Props={company:string;go:(page:string)=>void;onPreview:()=>void;connectionError:string};
export default function Assistant({company,go,onPreview,connectionError}:Props){
  const data=useCompany(company);
  const {config}=data;
  const published=data.sources.filter(source=>source.status==='Demo published').length;
  const ready=data.sources.filter(source=>source.status==='Demo published'&&source.indexStatus==='ready').length;
  const waiting=data.conversations.filter(conversation=>conversation.status==='HUMAN_REQUESTED').length;
  const storageReady=!connectionError&&data.database?.status==='ok';
  const steps=[
    {icon:'appearance',title:'Make it feel like you',description:'Your name, colors and a welcome in your own words.',label:'Edit appearance',page:'appearance',detail:'Brand configured'},
    {icon:'knowledge',title:'Give it the right knowledge',description:'Upload, publish and index the websites and files your answers will come from.',label:'Manage knowledge',page:'knowledge',detail:ready+' sources ready'},
    {icon:'channels',title:'Bring it to your customers',description:'Preview your website widget and prepare your channel setup.',label:'Explore channels',page:'channels',detail:'Local website preview'},
  ];
  const statuses=[
    {icon:'shield',label:'Workspace storage',value:storageReady?'Saved on this PC':'Connection needs attention',detail:storageReady?'Accounts, files and conversations persist.':'Check the connection notice above.'},
    {icon:'knowledge',label:'Knowledge library',value:`${ready} ${ready===1?'source':'sources'} ready`,detail:`${published} published · ${data.sources.length-published} drafts. Publish, then wait for Ready.`},
    {icon:'inbox',label:'Human handoff',value:waiting?`${waiting} waiting`:'Your team can take over',detail:'From your 50 most recent conversations.'},
  ];
  return <div className="space-y-6">
    <Card className="overflow-hidden"><div className="grid lg:grid-cols-2">
      <div className="flex flex-col p-7 lg:p-10"><Badge variant="secondary" className="w-fit"><Icon name="sparkle"/> One assistant for your business</Badge><h2 className="mt-6 text-3xl font-semibold tracking-tight lg:text-4xl">{config.botName}</h2><p className="mt-3 text-base text-foreground">A welcome that feels like {config.name}.</p><p className="mt-4 max-w-md text-sm text-muted-foreground">One assistant, shaped around your brand and the knowledge you choose to share.</p><div className="mt-6 flex flex-wrap gap-2"><Button onClick={onPreview}>Open your preview <Icon name="arrow"/></Button><Button variant="outline" onClick={()=>go('appearance')}><Icon name="appearance"/>Customize</Button></div><div className="mt-auto flex items-center gap-2 pt-10 text-xs text-muted-foreground"><span className="size-2 rounded-full bg-primary"/>Local AI assistant<Separator orientation="vertical" className="h-4!"/>Answers use Ready sources</div></div>
      <div className="flex min-h-[25rem] flex-col bg-accent p-6"><div className="flex justify-between text-xs font-semibold uppercase tracking-wider">The face of your business <Icon name="sparkle"/></div><div className="flex flex-1 items-center justify-center py-5 [&_img]:max-h-40"><Mascot src={config.avatar}/></div><Card className="mx-auto w-full max-w-xs gap-3 bg-card py-4"><CardHeader className="flex flex-row items-center gap-2 px-4"><Avatar className="size-9"><AvatarImage src={config.avatar}/><AvatarFallback>{config.botName[0]}</AvatarFallback></Avatar><div className="min-w-0 flex-1"><CardTitle className="truncate text-sm">{config.botName}</CardTitle><CardDescription className="truncate text-xs">{config.name}</CardDescription></div><Badge variant="outline">Preview</Badge></CardHeader><CardContent className="px-4 text-sm">{config.welcome}</CardContent><CardFooter className="px-4"><Button size="sm" variant="link" className="px-0" onClick={onPreview}>Say hello <Icon name="arrow"/></Button></CardFooter></Card><p className="mt-4 text-center text-xs text-muted-foreground">Your colors. Your voice. Your assistant.</p></div>
    </div></Card>
    <div className="grid gap-4 md:grid-cols-3" aria-label="Assistant status">{statuses.map(status=><Card key={status.label}><CardHeader className="flex flex-row items-start gap-3"><span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon name={status.icon}/></span><div><CardDescription>{status.label}</CardDescription><CardTitle className="mt-1 text-base">{status.value}</CardTitle></div></CardHeader><CardContent className="text-xs text-muted-foreground">{status.detail}</CardContent></Card>)}</div>
    <section aria-labelledby="setup-heading"><div className="mb-4 flex items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-wider text-primary">Build your customer experience</p><h2 id="setup-heading" className="mt-2 text-2xl font-semibold tracking-tight">A few details. A more personal welcome.</h2></div><span className="text-xs text-muted-foreground">01 — 03</span></div><div className="grid gap-4 md:grid-cols-3">{steps.map((step,index)=><Card key={step.page}><CardHeader><div className="flex items-center justify-between"><span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon name={step.icon}/></span><span className="text-xs text-muted-foreground">0{index+1}</span></div><Badge variant="secondary" className="mt-4 w-fit">{step.detail}</Badge><CardTitle className="mt-3">{step.title}</CardTitle><CardDescription>{step.description}</CardDescription></CardHeader><CardFooter className="mt-auto"><Button variant="link" className="px-0" onClick={()=>go(step.page)}>{step.label}<Icon name="arrow"/></Button></CardFooter></Card>)}</div></section>
    <Card><CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4"><div><CardTitle>One assistant. Wherever you welcome people.</CardTitle><CardDescription>Website, WordPress and Shopify use your branded widget. Social channels have local setup only.</CardDescription></div><Button variant="outline" onClick={()=>go('channels')}>View channels <Icon name="arrow"/></Button></CardHeader></Card>
  </div>;
}
