export type Account={id:string;name:string;email:string;role:'owner'|'platform_admin';companyId:string|null;companyName:string|null;botId:string|null};
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
  const response=await fetch('/api'+path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...options.headers}});
  if(!response.ok){let message='The local service is unavailable. Please try again.';try{const body=await response.json();if(typeof body.detail==='string')message=body.detail;else if(response.status===422)message='Check the fields and try again.';}catch{/* unavailable service */}
    if(response.status===401&&(path.startsWith('/company/')||path.startsWith('/platform/'))){
      message=path==='/company/sources/upload'?'Your session expired before the file was saved. Sign in, then select and upload it again.':'Your session expired. Sign in, then retry your action.';
      window.dispatchEvent(new CustomEvent('h4t-auth-expired',{detail:message}));
    }
    throw new Error(message);
  }
  return response.status===204?undefined as T:response.json();
}
