import type {ButtonHTMLAttributes, InputHTMLAttributes, ReactNode} from 'react';
import {Activity, ArrowUpRight, BookOpen, Bot, ChartNoAxesCombined, Code2, Download, Eye, Filter, Globe2, LockKeyhole, LogOut, Menu, MessageCircle, Moon, Palette, PlugZap, Search, Send, Settings, ShieldCheck, ShoppingBag, Sparkles, Sun, Trash2, UserRound, UsersRound, X} from 'lucide-react';
import {Button as ShadButton} from '@/components/ui/button';
import {Badge as ShadBadge} from '@/components/ui/badge';
import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';
import {cn} from '@/lib/utils';

const icons:Record<string,typeof Bot>={overview:ChartNoAxesCombined,billing:Activity,inbox:MessageCircle,knowledge:BookOpen,appearance:Palette,install:PlugZap,channels:PlugZap,bots:Bot,assistant:Bot,website:Globe2,web:Globe2,user:UserRound,close:X,send:Send,lock:LockKeyhole,shield:ShieldCheck,sparkle:Sparkles,arrow:ArrowUpRight,whatsapp:MessageCircle,facebook:MessageCircle,shopify:ShoppingBag,wordpress:Code2,menu:Menu,moon:Moon,sun:Sun,logout:LogOut,search:Search,filter:Filter,eye:Eye,download:Download,trash:Trash2,settings:Settings,team:UsersRound};
export function Icon({name}:{name:string}){const Component=icons[name]??Bot;return <Component className="icon size-4 shrink-0" aria-hidden="true"/>;}
export function Button({children,variant='secondary',className='',...props}:ButtonHTMLAttributes<HTMLButtonElement>&{variant?:'primary'|'secondary'|'ghost';children:ReactNode}){
  return <ShadButton variant={variant==='primary'?'default':variant==='ghost'?'ghost':'outline'} className={cn('button',variant,className)} {...props}>{children}</ShadButton>;
}
export function Field({label,hint,...props}:InputHTMLAttributes<HTMLInputElement>&{label:string;hint?:string}){
  return <Label className="field"><span>{label}{props.required&&<span className="required"> *</span>}</span><Input {...props}/>{hint&&<small>{hint}</small>}</Label>;
}
export function Badge({children,tone='neutral'}:{children:ReactNode;tone?:string}){
  return <ShadBadge variant={tone==='warning'?'outline':'secondary'} className={cn('badge',tone)}>{children}</ShadBadge>;
}
export function Brand(){return <a className="brand" href="/"><img src="/assets/brand/favicon.png" alt=""/><span>H4T<span className="brand-light"> Bot</span><small>by High4Tech</small></span></a>;}
export function Mascot({src='/assets/brand/mascots.svg'}:{src?:string}){return <img className="mascot" src={src} alt="Company assistant"/>;}
