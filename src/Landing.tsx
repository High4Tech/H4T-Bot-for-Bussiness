import Widget from './Widget';
import {Brand,Icon,Mascot} from './ui';
import {Button as ShadButton} from '@/components/ui/button';

export default function Landing(){
  return <div className="h4t-landing">
    <header className="h4t-site-header">
      <Brand/>
      <nav aria-label="Main navigation">
        <a href="#how-it-works">How it works</a>
        <a href="#preview">Try the assistant</a>
        <a href="/login">Sign in</a>
        <ShadButton asChild><a href="/signup">Create workspace <Icon name="arrow"/></a></ShadButton>
      </nav>
    </header>
    <main>
      <section className="h4t-hero" aria-labelledby="h4t-hero-title">
        <div className="h4t-hero-copy">
          <p className="h4t-product-line"><span className="h4t-product-mark"/> H4T Bot by High4Tech</p>
          <h1 id="h4t-hero-title">Your business knows the answer. Now your assistant can, too.</h1>
          <p className="h4t-hero-description">Give visitors one branded place to ask. Publish your website or documents, and your assistant can answer from that knowledge with sources. When a person is needed, your team can take over.</p>
          <div className="h4t-hero-actions">
            <ShadButton asChild size="lg"><a href="/signup">Create your workspace <Icon name="arrow"/></a></ShadButton>
            <a className="h4t-text-link" href="#preview">Try the sample assistant <Icon name="arrow"/></a>
          </div>
          <div className="h4t-hero-proof" aria-label="Product capabilities">
            <span><Icon name="knowledge"/> Published knowledge</span>
            <span><Icon name="shield"/> Source-backed replies</span>
            <span><Icon name="user"/> Human handoff</span>
          </div>
        </div>
        <div className="h4t-preview-stage" id="preview">
          <div className="h4t-stage-heading"><span>Meet your website assistant</span><span>Interactive sample</span></div>
          <div className="h4t-stage-monogram" aria-hidden="true">H4T</div>
          <div className="h4t-stage-widget"><Widget company="high4tech"/></div>
          <p className="h4t-stage-note">This sample uses scripted replies. Your workspace uses local AI after you publish knowledge.</p>
        </div>
      </section>

      <section className="h4t-process" id="how-it-works" aria-labelledby="h4t-process-title">
        <div className="h4t-section-intro">
          <p>From what you know to what customers need</p>
          <h2 id="h4t-process-title">One assistant, grounded in your business.</h2>
        </div>
        <div className="h4t-process-grid">
          <article><span className="h4t-step">01</span><Icon name="knowledge"/><h3>Add your knowledge</h3><p>Bring in your website and files. Keep drafts separate until you are ready to use them.</p></article>
          <article><span className="h4t-step">02</span><Icon name="sparkle"/><h3>Publish and index</h3><p>Make approved sources available to the assistant. See when each source is Ready.</p></article>
          <article><span className="h4t-step">03</span><Icon name="inbox"/><h3>Answer or hand off</h3><p>Visitors get grounded replies with citations. Your team can step in when the answer needs a person.</p></article>
        </div>
      </section>

      <section className="h4t-platform-note" aria-labelledby="h4t-platform-title">
        <div><span className="h4t-platform-icon"><Icon name="website"/></span><div><h2 id="h4t-platform-title">Start on your website.</h2><p>Install one branded widget on a local test page. WhatsApp, Messenger and store-specific connectors are planned for later stages.</p></div></div>
        <a href="/demo-host.html">Open the website demo <Icon name="arrow"/></a>
      </section>

      <section className="h4t-final-cta">
        <div><p>Built for the conversation after hello</p><h2>Let your business speak for itself.</h2><span>Create your workspace, publish a source, and try the assistant locally.</span><ShadButton asChild size="lg"><a href="/signup">Get started <Icon name="arrow"/></a></ShadButton></div>
        <Mascot/>
      </section>
    </main>
    <footer className="h4t-site-footer"><Brand/><span>H4T Bot is a local product preview by High4Tech.</span><a href="/login">Open workspace <Icon name="arrow"/></a></footer>
  </div>;
}
