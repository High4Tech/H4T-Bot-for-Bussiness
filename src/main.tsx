import React,{Suspense,lazy,useEffect,useState} from 'react';
import {createRoot,type Root} from 'react-dom/client';
import {AuthProvider,AuthScreen,Guard} from './Auth';
import {api} from './api';
import type {BotConfig} from './demo-model.mjs';
import './styles.css';
import './premium.css';
import './refinement.css';
import './go.css';
import './design-pass.css';
const Dashboard=lazy(()=>import('./Dashboard'));
const Platform=lazy(()=>import('./Platform'));
const Widget=lazy(()=>import('./Widget'));
const Landing=lazy(()=>import('./Landing'));
function PublicWidget(){
 const candidate=new URLSearchParams(location.search).get('company')||'high4tech';const company=/^(cedar|high4tech|[a-f0-9]{32})$/.test(candidate)?candidate:'';
 const fixture=['high4tech','cedar'].includes(company);const [ready,setReady]=useState(false);const [error,setError]=useState('');
 useEffect(()=>{let live=true;import('./store').then(async store=>{if(!company)throw new Error('Assistant not found.');if(fixture)store.synchronizeDemo();else{const data=await api<{appearance:BotConfig}>('/embed/'+company);if(live)store.initializeWorkspace(company,data.appearance);}if(live)setReady(true);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[company,fixture]);
 return <div className="standalone-widget">{error?<div className="loading-page" role="alert">{error}</div>:ready?<Widget company={company}/>:<div className="loading-page">Opening assistant…</div>}</div>;
}
const path=location.pathname;
const appRoot:Root=import.meta.hot?.data.root??createRoot(document.getElementById('root')!);
if(import.meta.hot)import.meta.hot.dispose(data=>{data.root=appRoot;});
const fallback=<div className="loading-page">Loading your local workspace…</div>;
appRoot.render(<React.StrictMode><Suspense fallback={fallback}>{path==='/widget'?<PublicWidget/>:path==='/'?<Landing/>:<AuthProvider>{path==='/platform'?<Guard platform><Platform/></Guard>:path.startsWith('/dashboard')?<Guard><Dashboard/></Guard>:<AuthScreen/>}</AuthProvider>}</Suspense></React.StrictMode>);
