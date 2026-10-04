import {useSyncExternalStore} from 'react';
import {companyDefaults, allowedTransition, mergeDemoConversations, type BotConfig} from './demo-model.mjs';
import {api} from './api';
export type Message = {id:string;role:'visitor'|'bot'|'agent';text:string};
export type Conversation = {id:string;company:string;name:string;email:string;status:string;messages:Message[]};
export type Source = {id:string;name:string;kind:'Website'|'File';status:'Demo published'|'Draft';version:number};
export type Company = {config:BotConfig;sources:Source[];conversations:Conversation[]};
const configKey = 'h4t.demo.appearance.v1';
function savedConfigs(): Record<string,BotConfig> {
  try {
    const saved: unknown=JSON.parse(localStorage.getItem(configKey)??'{}');
    if(!saved || typeof saved!=='object')return {};
    const result:Record<string,BotConfig>={};
    for(const [id,value] of Object.entries(saved)){
      if(!(id in companyDefaults)||!value||typeof value!=='object')continue;
      const v=value as Record<string,unknown>;
      if(['name','botName','welcome','description','avatar','logo','position','color'].some(k=>typeof v[k]!=='string'))continue;
      if(!/^#[0-9a-f]{6}$/i.test(String(v.color))||!Array.isArray(v.questions)||!v.questions.every(q=>typeof q==='string')||typeof v.dark!=='boolean'||typeof v.leadForm!=='boolean')continue;
      result[id]=value as BotConfig;
    }
    return result;
  } catch {return {};}
}
const saved=savedConfigs();
let state: Record<string,Company> = Object.fromEntries(Object.entries(companyDefaults).map(([id,config])=>[id,{
  config:{...config,...saved[id]},
  sources:[{id:id+'-web',name:id==='cedar'?'cedar.example / about':'high4tech.example / services',kind:'Website',status:'Demo published',version:1},{id:id+'-file',name:'Sample FAQ.txt',kind:'File',status:'Draft',version:1}],
  conversations:[{id:id+'-sample',company:id,name:'Sample visitor',email:'visitor@example.test',status:'HUMAN_REQUESTED',messages:[{id:'sample1',role:'visitor',text:'Can I speak with your team?'},{id:'sample2',role:'bot',text:'Demo: your request is in the local inbox. No real notification was sent.'}]}]
}]));
const listeners=new Set<()=>void>();
let channel: BroadcastChannel | undefined;
try {channel=new BroadcastChannel('h4t-local-demo-v1');}catch {/* in-memory fallback */}
const sessions=new Set<string>();
const modifiedCompanies=new Set<string>();
const visitorSessions=new Map<string,string>();
export function visitorSession(company:string){return visitorSessions.get(company)??'';}
function emit() {listeners.forEach(fn=>fn());}
function publish(companyId:string) {emit();if(companyId in companyDefaults)channel?.postMessage({type:'company',id:companyId,value:state[companyId]});}
channel?.addEventListener('message',e=>{
  const d=e.data;
  if(d?.type==='sync-request' && typeof d.sender==='string') channel?.postMessage({type:'sync-response',target:d.sender,value:Object.fromEntries(Object.entries(state).filter(([id])=>id in companyDefaults))});
  if(d?.type==='sync-response' && sessions.has(d.target)){
    state=Object.fromEntries(Object.entries(state).map(([id,local])=>{
      const incoming=(id in companyDefaults?d.value?.[id]:undefined) as Company|undefined;
      if(!incoming)return [id,local];
      return [id,modifiedCompanies.has(id)?{...local,conversations:mergeDemoConversations(local.conversations,incoming.conversations)}:incoming];
    }));emit();
  }
  if(d?.type==='company' && d.id in companyDefaults){modifiedCompanies.add(d.id);state={...state,[d.id]:d.value};emit();}
});
export function synchronizeDemo() {const sender=crypto.randomUUID();sessions.add(sender);channel?.postMessage({type:'sync-request',sender});}
export function useCompany(id:string) { return useSyncExternalStore(fn=>{listeners.add(fn);return ()=>{listeners.delete(fn);};},()=>state[id]); }
function mutate(id:string,change:(c:Company)=>Company) {modifiedCompanies.add(id);state={...state,[id]:change(state[id])};publish(id);}
export function getConfig(id:string) {return state[id]?.config ?? state.high4tech.config;}
export function initializeWorkspace(id:string,config:BotConfig){state={...state,[id]:state[id]?{...state[id],config}:{config,sources:[],conversations:[]}};emit();}
export async function saveConfig(id:string,config:BotConfig) {const saved=id in companyDefaults?config:await api<BotConfig>('/company/appearance',{method:'PUT',body:JSON.stringify(config)});mutate(id,c=>({...c,config:saved}));if(id in companyDefaults)try{localStorage.setItem(configKey,JSON.stringify(Object.fromEntries(Object.entries(state).filter(([k])=>k in companyDefaults).map(([k,c])=>[k,c.config]))));}catch {/* fixture fallback */}}
export function startChat(company:string,name='Guest visitor',email='') {const id=crypto.randomUUID();visitorSessions.set(company,id);mutate(company,c=>({...c,conversations:[{id,company,name,email,status:'BOT_ACTIVE',messages:[]},...c.conversations]}));return id;}
export function addMessage(company:string,id:string,role:Message['role'],text:string) {mutate(company,c=>({...c,conversations:c.conversations.map(x=>x.id===id?{...x,messages:[...x.messages,{id:crypto.randomUUID(),role,text}]}:x)}));}
export function changeStatus(company:string,id:string,status:string) {mutate(company,c=>({...c,conversations:c.conversations.map(x=>x.id===id && allowedTransition(x.status,status)?{...x,status}:x)}));}
export function currentConversation(company:string,id:string) {return state[company].conversations.find(x=>x.id===id);}
export function addSource(company:string,name:string,kind:Source['kind']) {mutate(company,c=>({...c,sources:[...c.sources,{id:crypto.randomUUID(),name,kind,status:'Draft',version:1}]}));}
export function toggleSource(company:string,id:string) {mutate(company,c=>({...c,sources:c.sources.map(s=>s.id===id?{...s,status:s.status==='Draft'?'Demo published':'Draft',version:s.version+1}:s)}));}
export function removeSource(company:string,id:string) {mutate(company,c=>({...c,sources:c.sources.filter(s=>s.id!==id)}));}
