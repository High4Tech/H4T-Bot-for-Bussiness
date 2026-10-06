import {useEffect,useState} from 'react';
import {api} from './api';
import {useAuth} from './Auth';
import {Badge,Brand,Button,Icon} from './ui';
// The operator receives only allowlisted metadata; no customer store is imported.
type Metadata={id:string;name:string;botId:string;plan:string;status:string;answers:number};
export default function Platform(){
 const [companies,setCompanies]=useState<Metadata[]>([]);const [error,setError]=useState('');const {logout}=useAuth();
 useEffect(()=>{api<Metadata[]>('/platform/companies').then(setCompanies).catch(e=>setError(e.message));},[]);
 return <div className="platform"><header><Brand/><Button onClick={()=>logout().catch(e=>setError(e.message))}>Sign out<Icon name="logout"/></Button></header><main><span className="eyebrow">HIGH4TECH · PLATFORM</span><h1>A clear view of the platform.</h1><p>Account metadata and aggregate usage. Customer content stays outside this surface.</p><div className="demo-notice"><Icon name="shield"/><strong>Privacy boundary</strong><span>No inbox, visitor details, knowledge, impersonation or conversation exports.</span></div>{error&&<p role="alert" className="form-error">{error}</p>}<div className="metrics">{[['Local companies',companies.length],['Business assistants',companies.length],['AI answers',companies.reduce((total,c)=>total+c.answers,0)]].map(([label,value])=><div className="panel metric" key={label}><div><p>{label}</p><strong>{value}</strong><small>Local development</small></div></div>)}</div><section className="panel"><div className="section-heading"><h2>Companies</h2><Badge>Metadata only</Badge></div><div className="table-scroll"><table><thead><tr><th>Company</th><th>Plan</th><th>Assistant</th><th>AI usage</th><th>Status</th></tr></thead><tbody>{companies.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.plan}</td><td>1</td><td>{c.answers}</td><td><Badge>{c.status}</Badge></td></tr>)}</tbody></table>{!companies.length&&!error&&<div className="empty-state">No local business accounts yet.</div>}</div></section><p className="subtle">Billing changes, account suspension and audited operator actions remain deferred.</p></main></div>;
}
