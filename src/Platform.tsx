import {Alert,AlertDescription,AlertTitle} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Card,CardContent,CardDescription,CardHeader,CardTitle} from '@/components/ui/card';
import {Table,TableHeader,TableBody,TableRow,TableHead,TableCell} from '@/components/ui/table';
import {useEffect,useState} from 'react';
import {api} from './api';
import {useAuth} from './Auth';
import {Brand,Icon} from './ui';

// Operator responses are an allowlist of metadata and aggregate usage only.
type Metadata={id:string;name:string;botId:string;plan:string;status:string;answers:number};
export default function Platform(){
 const [companies,setCompanies]=useState<Metadata[]>([]);const [error,setError]=useState('');const {logout}=useAuth();
 useEffect(()=>{api<Metadata[]>('/platform/companies').then(setCompanies).catch(e=>setError(e.message));},[]);
 const metrics=[['Local companies',companies.length],['Business assistants',companies.length],['AI answers',companies.reduce((total,c)=>total+c.answers,0)]] as const;
 return <div className="min-h-screen bg-background text-foreground"><header className="border-b"><div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4"><Brand/><Button variant="outline" onClick={()=>logout().catch(e=>setError(e.message))}>Sign out<Icon name="logout"/></Button></div></header><main className="mx-auto max-w-7xl space-y-6 px-6 py-10"><div><Badge variant="secondary">High4Tech · platform</Badge><h1 className="mt-4">A clear view of the platform.</h1><p className="mt-2">Account metadata and aggregate usage. Customer content stays outside this surface.</p></div><Alert><Icon name="shield"/><AlertTitle>Privacy boundary</AlertTitle><AlertDescription>No inbox, visitor details, knowledge, impersonation or conversation exports.</AlertDescription></Alert>{error&&<Alert variant="destructive" role="alert"><AlertTitle>Connection interrupted</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}<div className="grid gap-4 md:grid-cols-3">{metrics.map(([label,value])=><Card key={label}><CardHeader><CardDescription>{label}</CardDescription><CardTitle className="text-3xl tabular-nums">{value}</CardTitle></CardHeader><CardContent className="text-xs text-muted-foreground">Local development</CardContent></Card>)}</div><Card><CardHeader className="flex flex-row items-center justify-between"><div><CardTitle>Companies</CardTitle><CardDescription>Subscription and usage metadata</CardDescription></div><Badge variant="outline">Metadata only</Badge></CardHeader><CardContent className="px-0"><div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Company</TableHead><TableHead>Plan</TableHead><TableHead>Assistant</TableHead><TableHead>AI usage</TableHead><TableHead>Status</TableHead></TableRow></TableHeader><TableBody>{companies.map(c=><TableRow key={c.id}><TableCell>{c.name}</TableCell><TableCell>{c.plan}</TableCell><TableCell>1</TableCell><TableCell>{c.answers}</TableCell><TableCell><Badge variant="secondary">{c.status}</Badge></TableCell></TableRow>)}</TableBody></Table>{!companies.length&&!error&&<p className="p-8 text-center text-sm text-muted-foreground">No local business accounts yet.</p>}</div></CardContent></Card><p className="text-xs">Billing changes, account suspension and audited operator actions remain deferred.</p></main></div>;
}
