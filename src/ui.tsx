import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';
import {ChartBarIcon} from '@phosphor-icons/react/dist/csr/ChartBar';
import {ChatCircleDotsIcon} from '@phosphor-icons/react/dist/csr/ChatCircleDots';
import {BooksIcon} from '@phosphor-icons/react/dist/csr/Books';
import {PaletteIcon} from '@phosphor-icons/react/dist/csr/Palette';
import {PlugIcon} from '@phosphor-icons/react/dist/csr/Plug';
import {RobotIcon} from '@phosphor-icons/react/dist/csr/Robot';
import {GlobeIcon} from '@phosphor-icons/react/dist/csr/Globe';
import {UserIcon} from '@phosphor-icons/react/dist/csr/User';
import {XIcon} from '@phosphor-icons/react/dist/csr/X';
import {PaperPlaneTiltIcon} from '@phosphor-icons/react/dist/csr/PaperPlaneTilt';
import {LockKeyIcon} from '@phosphor-icons/react/dist/csr/LockKey';
import {ShieldCheckIcon} from '@phosphor-icons/react/dist/csr/ShieldCheck';
import {SparkleIcon} from '@phosphor-icons/react/dist/csr/Sparkle';
import {ArrowUpRightIcon} from '@phosphor-icons/react/dist/csr/ArrowUpRight';
import {WhatsappLogoIcon} from '@phosphor-icons/react/dist/csr/WhatsappLogo';
import {FacebookLogoIcon} from '@phosphor-icons/react/dist/csr/FacebookLogo';
import {ShoppingBagIcon} from '@phosphor-icons/react/dist/csr/ShoppingBag';
import {CodeIcon} from '@phosphor-icons/react/dist/csr/Code';
import {ListIcon} from '@phosphor-icons/react/dist/csr/List';
import {MoonIcon} from '@phosphor-icons/react/dist/csr/Moon';
import {SunIcon} from '@phosphor-icons/react/dist/csr/Sun';
import {SignOutIcon} from '@phosphor-icons/react/dist/csr/SignOut';
const icons:Record<string,typeof ChartBarIcon>={overview:ChartBarIcon,billing:ChartBarIcon,inbox:ChatCircleDotsIcon,knowledge:BooksIcon,appearance:PaletteIcon,install:PlugIcon,channels:PlugIcon,bots:RobotIcon,assistant:RobotIcon,website:GlobeIcon,web:GlobeIcon,user:UserIcon,close:XIcon,send:PaperPlaneTiltIcon,lock:LockKeyIcon,shield:ShieldCheckIcon,sparkle:SparkleIcon,arrow:ArrowUpRightIcon,whatsapp:WhatsappLogoIcon,facebook:FacebookLogoIcon,shopify:ShoppingBagIcon,wordpress:CodeIcon,menu:ListIcon,moon:MoonIcon,sun:SunIcon,logout:SignOutIcon};
export function Icon({name}: {name: string}) {const Component=icons[name]??RobotIcon;return <Component className="icon" size={20} weight="regular" aria-hidden="true"/>;}
export function Button({ children, variant='secondary', className='', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & {variant?: 'primary'|'secondary'|'ghost'; children: ReactNode}) {
  return <button className={'button '+variant+' '+className} {...props}>{children}</button>;
}
export function Field({label, hint, ...props}: InputHTMLAttributes<HTMLInputElement> & {label: string; hint?: string}) {
  return <label className="field"><span>{label}{props.required && <span className="required"> *</span>}</span><input {...props}/>{hint && <small>{hint}</small>}</label>;
}
export function Badge({children, tone='neutral'}:{children: ReactNode; tone?: string}) { return <span className={'badge '+tone}>{children}</span>; }
export function Brand() { return <a className="brand" href="/"><img src="/assets/brand/favicon.png" alt=""/><span>H4T<span className="brand-light"> Bot</span><small>by High4Tech</small></span></a>; }
export function Mascot({src='/assets/brand/mascots.svg'}:{src?: string}) { return <img className="mascot" src={src} alt="Company assistant"/>; }
