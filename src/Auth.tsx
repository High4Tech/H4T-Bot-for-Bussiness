import {createContext,useContext,useEffect,useState,type ReactNode,type FormEvent} from 'react';
import {api,type Account} from './api';
import {Brand,Button,Field,Icon,Mascot} from './ui';
type AuthState={user:Account|null;loading:boolean;setUser:(user:Account|null)=>void;logout:()=>Promise<void>};
const Context=createContext<AuthState>(null!);
export function useAuth(){return useContext(Context);}
export function AuthProvider({children}:{children:ReactNode}){
 const [user,setUser]=useState<Account|null>(null);const [loading,setLoading]=useState(true);
 useEffect(()=>{let live=true;api<Account>('/auth/me').then(value=>{if(live)setUser(value);}).catch(()=>{}).finally(()=>{if(live)setLoading(false);});return()=>{live=false;};},[]);
 async function logout(){await api('/auth/logout',{method:'POST'});setUser(null);location.assign('/login');}
 return <Context.Provider value={{user,loading,setUser,logout}}>{children}</Context.Provider>;
}
export function Guard({children,platform=false}:{children:ReactNode;platform?:boolean}){
 const {user,loading}=useAuth();
 if(loading)return <div className="loading-page">Opening your workspace…</div>;
 if(!user)return <AuthScreen/>;
 if(platform&&user.role!=='platform_admin')return <div className="access-message"><Brand/><Icon name="lock"/><h1>Platform access is restricted.</h1><p>This account belongs to your customer workspace.</p><a className="button primary" href="/dashboard">Return to workspace</a></div>;
 if(!platform&&user.role!=='owner')return <div className="access-message"><Brand/><h1>Your platform workspace is ready.</h1><a className="button primary" href="/platform">Open platform</a></div>;
 return children;
}
export function AuthScreen(){
 const {setUser,user}=useAuth();const [signup,setSignup]=useState(location.pathname==='/signup');const [pending,setPending]=useState(false);const [error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setPending(true);setError('');const form=new FormData(e.currentTarget);try{const account=await api<Account>(signup?'/auth/register':'/auth/login',{method:'POST',body:JSON.stringify(Object.fromEntries(form))});setUser(account);location.assign(account.role==='platform_admin'?'/platform':'/dashboard');}catch(e){setError((e as Error).message);}finally{setPending(false);}}
 if(user)return <div className="access-message"><Brand/><h1>Welcome back, {user.name}.</h1><a className="button primary" href={user.role==='platform_admin'?'/platform':'/dashboard'}>Open your workspace</a></div>;
 return <div className="auth-page"><section className="auth-story"><Brand/><div><span className="eyebrow">ONE ASSISTANT. YOUR WHOLE BUSINESS.</span><h1>A better hello<br/>starts here<span>.</span></h1><p>Your knowledge, your brand, and a single home for every conversation.</p><div className="auth-illustration"><Mascot/><span className="floating-note"><Icon name="sparkle"/> Made for your business</span></div></div><small>LOCAL PRODUCT PREVIEW · BY HIGH4TECH</small></section><section className="auth-form-wrap"><a className="auth-back" href="/">← Back to H4T Bot</a><form className="auth-form" onSubmit={submit}><div className="auth-symbol"><Icon name="lock"/></div><h1>{signup?'Make yourself at home.':'Good to see you again.'}</h1><p>{signup?'Create your local business workspace.':'Sign in to your business workspace.'}</p>{signup&&<><Field name="name" label="Your name" required minLength={2} maxLength={80} autoComplete="name"/><Field name="company" label="Business name" required minLength={2} maxLength={80} autoComplete="organization"/></>}<Field name="email" label="Email address" type="email" required maxLength={254} autoComplete="email"/><Field name="password" label="Password" type="password" required minLength={12} maxLength={128} autoComplete={signup?'new-password':'current-password'} hint="At least 12 characters"/>{error&&<p className="form-error" role="alert">{error}</p>}<Button variant="primary" disabled={pending}>{pending?'Opening workspace…':signup?'Create workspace':'Sign in'}<Icon name="arrow"/></Button><p className="auth-switch">{signup?'Already have an account?':'New to H4T Bot?'} <button type="button" onClick={()=>{setSignup(!signup);setError('');}}>{signup?'Sign in':'Create a workspace'}</button></p><div className="auth-local"><Icon name="shield"/><span>Account and settings stay on this PC.<br/>AI responses are still a scripted preview.</span></div></form></section></div>;
}
