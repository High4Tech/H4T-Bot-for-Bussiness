import {type ReactNode,useEffect} from 'react';
import {Alert,AlertDescription,AlertTitle} from '@/components/ui/alert';
import {Avatar,AvatarFallback} from '@/components/ui/avatar';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogHeader,DialogTitle} from '@/components/ui/dialog';
import {Separator} from '@/components/ui/separator';
import {
  Sidebar,SidebarContent,SidebarFooter,SidebarGroup,SidebarGroupLabel,SidebarHeader,
  SidebarInset,SidebarMenu,SidebarMenuBadge,SidebarMenuButton,SidebarMenuItem,
  SidebarProvider,SidebarTrigger,
} from '@/components/ui/sidebar';
import {Brand,Icon} from './ui';
import Widget from './Widget';

type NavItem={id:string;label:string};
const groups:{label:string;items:NavItem[]}[]=[
  {label:'Workspace',items:[{id:'overview',label:'Dashboard'},{id:'inbox',label:'Chat record'}]},
  {label:'Assistant',items:[{id:'assistant',label:'Your assistant'},{id:'knowledge',label:'Knowledge'},{id:'channels',label:'Integrations'},{id:'appearance',label:'Appearance'}]},
  {label:'Manage',items:[{id:'team',label:'Users'},{id:'settings',label:'Settings'},{id:'billing',label:'Pricing'}]},
];

type Props={
  company:string;business:string;active:string;title:string;description:string;
  user:{name:string;email:string};waiting:number;dark:boolean;onDark:()=>void;
  onSignOut:()=>void;onSearch:()=>void;onPreview:()=>void;previewOpen:boolean;
  onPreviewOpen:(open:boolean)=>void;onNavigate:(id:string)=>void;error:string;children:ReactNode;
};
export default function DashboardShell(props:Props){
  const {company,business,active,title,description,user,waiting,dark,onDark,onSignOut,onSearch,onPreview,previewOpen,onPreviewOpen,onNavigate,error,children}=props;
  useEffect(()=>{document.documentElement.classList.toggle('dark',dark);return()=>document.documentElement.classList.remove('dark');},[dark]);
  return <SidebarProvider>
    <Sidebar collapsible="offcanvas" variant="sidebar">
      <SidebarHeader className="px-4 py-5"><Brand/><Button variant="outline" className="mt-5 w-full justify-start text-muted-foreground" onClick={onSearch}><Icon name="search"/> Search conversations <kbd className="ml-auto text-xs">Ctrl K</kbd></Button></SidebarHeader>
      <SidebarContent>
        {groups.map(group=><SidebarGroup key={group.label}>
          <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
          <SidebarMenu>{group.items.map(item=><SidebarMenuItem key={item.id}>
            <SidebarMenuButton asChild isActive={active===item.id} onClick={()=>onNavigate(item.id)}><a href={'#/'+item.id}><Icon name={item.id}/><span>{item.label}</span></a></SidebarMenuButton>
            {item.id==='inbox'&&waiting>0&&<SidebarMenuBadge>{waiting}</SidebarMenuBadge>}
          </SidebarMenuItem>)}</SidebarMenu>
        </SidebarGroup>)}
      </SidebarContent>
      <SidebarFooter className="gap-3 p-3">
        <Button variant="outline" className="w-full justify-start" onClick={onPreview}><Icon name="eye"/> Try in browser</Button>
        <Separator/>
        <div className="flex min-w-0 items-center gap-2 px-1">
          <Avatar className="size-9"><AvatarFallback>{user.name.slice(0,1).toUpperCase()}</AvatarFallback></Avatar>
          <div className="min-w-0 flex-1"><div className="truncate text-sm font-medium">{user.name}</div><div className="truncate text-xs text-muted-foreground">{user.email}</div></div>
          <Button size="icon" variant="ghost" aria-label="Sign out" onClick={onSignOut}><Icon name="logout"/></Button>
        </div>
      </SidebarFooter>
    </Sidebar>
    <SidebarInset className="min-w-0 bg-background">
      <header className="flex h-16 items-center justify-between gap-4 border-b px-5 lg:px-8">
        <div className="flex min-w-0 items-center gap-3 text-sm"><SidebarTrigger/><Separator orientation="vertical" className="h-5!"/><span className="hidden truncate text-muted-foreground sm:inline">{business}</span><span className="hidden text-muted-foreground sm:inline">/</span><strong className="truncate font-medium">{title}</strong></div>
        <div className="flex items-center gap-2"><Badge variant="secondary" className="hidden sm:inline-flex">{error?'Connection interrupted':'Local workspace'}</Badge><Button size="icon" variant="ghost" aria-label={dark?'Switch to light mode':'Switch to dark mode'} onClick={onDark}><Icon name={dark?'sun':'moon'}/></Button><Avatar className="size-8"><AvatarFallback>{user.name.slice(0,1).toUpperCase()}</AvatarFallback></Avatar></div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-7 lg:px-8 lg:py-9">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-3xl font-semibold tracking-tight">{title}</h1><p className="mt-1 text-sm text-muted-foreground">{description}</p></div><Button onClick={onPreview}><Icon name="eye"/>Try in browser</Button></div>
        <Alert className="mb-6"><Icon name="sparkle"/><AlertTitle>Local preview</AlertTitle><AlertDescription>Saved on this PC. Published, Ready knowledge powers local AI replies; billing is Demo.</AlertDescription></Alert>
        {error&&<Alert variant="destructive" className="mb-5"><AlertTitle>Connection interrupted</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
        {children}
        <footer className="mt-10 flex flex-wrap justify-between gap-3 border-t pt-5 text-xs text-muted-foreground"><span>H4T Bot by High4Tech</span><span>Local prototype · No cloud services</span></footer>
      </main>
    </SidebarInset>
    <Dialog open={previewOpen} onOpenChange={onPreviewOpen}><DialogContent className="h-[min(42rem,calc(100vh-2rem))] max-w-sm overflow-hidden border-0 p-0 [&>button]:z-20"><DialogHeader className="sr-only"><DialogTitle>Assistant preview</DialogTitle></DialogHeader><Widget key={company} company={company} onClose={()=>onPreviewOpen(false)}/></DialogContent></Dialog>
  </SidebarProvider>;
}
