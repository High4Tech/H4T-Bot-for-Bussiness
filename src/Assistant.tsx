import type {CSSProperties} from 'react';
import {useCompany} from './store';
import {Badge,Button,Icon,Mascot} from './ui';

type Props={company:string;go:(page:string)=>void;onPreview:()=>void;connectionError:string};

export default function Assistant({company,go,onPreview,connectionError}:Props){
  const data=useCompany(company);
  const {config}=data;
  const published=data.sources.filter(source=>source.status==='Demo published').length;
  const ready=data.sources.filter(source=>source.status==='Demo published'&&source.indexStatus==='ready').length;
  const waiting=data.conversations.filter(conversation=>conversation.status==='HUMAN_REQUESTED').length;
  const storageReady=!connectionError&&data.database?.status==='ok';
  const steps=[
    {icon:'appearance',title:'Make it feel like you',description:'Your name, colors and a welcome in your own words.',label:'Edit appearance',page:'appearance',detail:'Brand configured'},
    {icon:'knowledge',title:'Give it the right knowledge',description:'Upload, publish and index the websites and files your answers will come from.',label:'Manage knowledge',page:'knowledge',detail:ready+' sources ready'},
    {icon:'channels',title:'Bring it to your customers',description:'Preview your website widget and prepare your channel setup.',label:'Explore channels',page:'channels',detail:'Local website preview'},
  ];

  return <div className="assistant-page">
    <section className="panel assistant-hero">
      <div className="assistant-identity">
        <div className="assistant-kicker"><span className="brand-spark"><Icon name="sparkle"/></span><span>YOUR BUSINESS, IN EVERY CONVERSATION</span></div>
        <h2>{config.botName}</h2>
        <p>A familiar face.<br/><span>A welcome that feels like {config.name}.</span></p>
        <div className="assistant-description">One assistant, shaped around your brand and the knowledge you choose to share.</div>
        <div className="action-row"><Button variant="primary" onClick={onPreview}>Open your preview <Icon name="arrow"/></Button><Button onClick={()=>go('appearance')}><Icon name="appearance"/>Customize</Button></div>
        <div className="assistant-identity-foot"><span className="assistant-mode-dot"/>Local AI assistant<span className="separator-dot">·</span>Answers use Ready sources</div>
      </div>
      <div className="assistant-brand-stage" style={{'--business-accent':config.color} as CSSProperties}>
        <div className="assistant-stage-label"><span>THE FACE OF YOUR BUSINESS</span><Icon name="sparkle"/></div>
        <div className="assistant-avatar-plinth"><Mascot src={config.avatar}/></div>
        <div className="assistant-welcome-card"><div><span className="welcome-avatar"><Mascot src={config.avatar}/></span><div><strong>{config.botName}</strong><small>{config.name}</small></div><span className="welcome-preview-label">Preview</span></div><p>{config.welcome}</p><button onClick={onPreview}>Say hello <Icon name="arrow"/></button></div>
        <div className="assistant-stage-footer">Your colors. Your voice. Your assistant.</div>
      </div>
    </section>

    <div className="assistant-status-grid" aria-label="Assistant status">
      <section className="panel assistant-status"><span className="status-symbol"><Icon name="shield"/></span><div><span>Workspace storage</span><strong>{storageReady?'Saved on this PC':'Connection needs attention'}</strong><small>{storageReady?'Accounts, files and conversations persist.':'Check the connection notice above.'}</small></div></section>
      <section className="panel assistant-status"><span className="status-symbol"><Icon name="knowledge"/></span><div><span>Knowledge library</span><strong>{ready} {ready===1?'source':'sources'} ready for answers</strong><small>{published} published · {data.sources.length-published} drafts. Publish, then wait for Ready.</small></div></section>
      <section className="panel assistant-status"><span className="status-symbol"><Icon name="inbox"/></span><div><span>Human handoff</span><strong>{waiting?`${waiting} ${waiting===1?'conversation':'conversations'} waiting`:'Your team can take over'}</strong><small>From your 50 most recent conversations.</small></div></section>
    </div>

    <section className="assistant-setup" aria-labelledby="setup-heading"><div className="assistant-section-heading"><div><span className="eyebrow">BUILD YOUR CUSTOMER EXPERIENCE</span><h2 id="setup-heading">A few details. A more personal welcome.</h2></div><span className="setup-count">01 — 03</span></div><div className="assistant-setup-grid">{steps.map((step,index)=><article className="panel assistant-step" key={step.page}><div className="assistant-step-top"><span className="status-symbol"><Icon name={step.icon}/></span><span>0{index+1}</span></div><Badge>{step.detail}</Badge><h3>{step.title}</h3><p>{step.description}</p><button onClick={()=>go(step.page)}>{step.label}<Icon name="arrow"/></button></article>)}</div></section>

    <section className="panel assistant-channel-row"><div><h2>One assistant. Wherever you welcome people.</h2><p>Website, WordPress and Shopify use your branded widget. Social channels have local setup only.</p></div><div className="assistant-channel-icons" aria-label="Available setup channels">{[['web','Website'],['wordpress','WordPress'],['shopify','Shopify'],['whatsapp','WhatsApp'],['facebook','Facebook']].map(([icon,label])=><span key={icon} role="img" aria-label={label} title={label}><Icon name={icon}/></span>)}</div><Button variant="ghost" onClick={()=>go('channels')}>View channels <Icon name="arrow"/></Button></section>
  </div>;
}
