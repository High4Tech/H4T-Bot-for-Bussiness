import {useState,type FormEvent} from 'react';
import {addSource,processSource,removeSource,toggleSource,uploadSource,useCompany,type Source} from './store';
import {Badge,Button,Field,Icon} from './ui';

const indexLabels:Record<string,string>={ready:'Ready',queued:'Queued',running:'Processing',failed:'Needs attention',deferred:'Waiting',obsolete:'Outdated'};
const errorLabels:Record<string,string>={
  no_readable_text:'No readable text found. Scanned PDFs need OCR.',
  pdf_no_extractable_text:'This PDF has no extractable text. Scanned pages need OCR.',
  file_extract_failed:'Could not read this file. Check that it opens normally.',
  file_integrity_failed:'The stored file changed. Upload it again.',
  file_missing:'The stored file is missing. Upload it again.',
  embedding_model_missing:'The local embedding model is missing.',
  indexing_failed:'Indexing failed. Please retry.',
};

function IndexStatus({source}:{source:Source}){
  if(source.status==='Draft')return <Badge>Not published</Badge>;
  const status=source.indexStatus||'deferred';
  return <Badge tone={status==='ready'?'success':status==='failed'?'warning':'neutral'}>{indexLabels[status]||status}</Badge>;
}

export default function Knowledge({company}:{company:string}){
  const data=useCompany(company);
  const [url,setUrl]=useState('');
  const [notice,setNotice]=useState('');
  const [kind,setKind]=useState<'website'|'file'|''>('');
  const [busy,setBusy]=useState(false);
  const [savedId,setSavedId]=useState('');
  const savedDraft=data.sources.find(source=>source.id===savedId&&source.status==='Draft');

  async function act(task:()=>Promise<void>){
    if(busy)return;
    setBusy(true);setNotice('');
    try{await task();}catch(error){setNotice((error as Error).message);}finally{setBusy(false);}
  }
  function saveWebsite(event:FormEvent){
    event.preventDefault();
    void act(async()=>{
      const parsed=new URL(url);
      if(!['http:','https:'].includes(parsed.protocol))throw new Error('Use a valid public http or https URL.');
      const id=await addSource(company,parsed.hostname+parsed.pathname,'Website',parsed.href);
      setSavedId(id||'');setUrl('');setKind('');
      setNotice('Website saved as a draft. Publish it to start indexing.');
    });
  }
  function publish(source:Source){
    void act(async()=>{
      await toggleSource(company,source.id);
      setSavedId('');
      setNotice(source.status==='Draft'?'Published. Indexing is queued; wait for Ready before testing the assistant.':'Unpublished. It will no longer be used in answers.');
    });
  }

  return <div className="knowledge-ai">
    <div className="source-cards">
      <button className="source-card" onClick={()=>setKind('website')}><span className="source-icon"><Icon name="website"/></span><h2>Website</h2><p>Save a public page for the assistant to read.</p><span>Add website ↗</span></button>
      <button className="source-card" onClick={()=>setKind('file')}><span className="source-icon"><Icon name="knowledge"/></span><h2>Upload a file</h2><p>TXT, PDF, DOCX or CSV, stored on this PC.</p><span>Add file ↗</span></button>
      <div className="source-explainer"><Badge>Knowledge indexing</Badge><h3>Answers start with<br/>published sources.</h3><p>Upload, publish, then wait for Ready. The assistant cites your business’s own text. Indexing updates knowledge, not model weights.</p></div>
    </div>
    {kind==='website'&&<form className="panel source-form" onSubmit={saveWebsite}>
      <Field label="Public website URL" type="url" required value={url} onChange={event=>setUrl(event.target.value)} placeholder="https://company.example/help"/>
      <Button variant="primary" disabled={busy}>Save draft</Button><Button type="button" onClick={()=>setKind('')}>Cancel</Button>
      <small>Only public text pages are supported; private network addresses and redirects are blocked.</small>
    </form>}
    {kind==='file'&&<div className="panel source-form">
      <label className="field">Local file<input type="file" accept=".txt,.pdf,.docx,.csv" disabled={busy} onChange={event=>{
        const file=event.target.files?.[0];if(!file)return;
        if(file.size>10*1024*1024){setNotice('Choose a file under 10 MB.');return;}
        void act(async()=>{
          const id=await uploadSource(company,file);
          setSavedId(id||'');setKind('');
          setNotice('File saved privately as a draft. Publish it to start indexing.');
        });
      }}/></label><Button onClick={()=>setKind('')}>Cancel</Button>
      <small>Text-based PDFs are supported. Scanned pages need OCR, which is not enabled yet.</small>
    </div>}
    {notice&&<p role="status" className="inline-notice">{notice}</p>}
    {savedDraft&&<div className="panel knowledge-next" role="status"><div><strong>Next: publish this source</strong><p>{savedDraft.name} is saved but cannot answer questions until you publish it and its index shows Ready.</p></div><Button variant="primary" disabled={busy} onClick={()=>publish(savedDraft)}>Publish & index <Icon name="arrow"/></Button></div>}
    <section className="panel">
      <div className="section-heading"><div><h2>Your sources <Badge>{data.sources.length}</Badge></h2><p>Only published sources marked Ready can be used in answers.</p></div></div>
      <div className="table-scroll"><table><thead><tr><th>Source</th><th>Type</th><th>Version</th><th>Publication</th><th>Index</th><th>Chunks</th><th>Actions</th></tr></thead><tbody>
        {data.sources.map(source=><tr key={source.id}>
          <td><span className="table-name"><Icon name={source.kind==='Website'?'website':'knowledge'}/>{source.name}</span></td>
          <td>{source.kind}</td><td>v{source.version}</td>
          <td><Badge tone={source.status==='Draft'?'neutral':'success'}>{source.status==='Draft'?'Draft':'Published'}</Badge></td>
          <td><IndexStatus source={source}/>{source.indexError&&<small className="knowledge-error">{errorLabels[source.indexError]||source.indexError.replaceAll('_',' ')}</small>}</td>
          <td>{source.chunks||'—'}</td>
          <td><div className="action-row">
            <Button disabled={busy} onClick={()=>publish(source)}>{source.status==='Draft'?'Publish & index':'Unpublish'}</Button>
            {source.status!=='Draft'&&['failed','deferred','obsolete'].includes(source.indexStatus||'')&&<Button disabled={busy} onClick={()=>void act(async()=>{await processSource(company,source.id);setNotice('Indexing queued again. Wait for Ready.');})}>Retry</Button>}
            <Button variant="ghost" disabled={busy} onClick={()=>void act(()=>removeSource(company,source.id))}>Archive</Button>
          </div></td>
        </tr>)}
      </tbody></table>{!data.sources.length&&<div className="empty-state">No sources saved. Add a website or file above.</div>}</div>
    </section>
  </div>;
}
