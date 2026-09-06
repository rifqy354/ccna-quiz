import Link from 'next/link';
import SiteHeader from '@/components/SiteHeader';

export default function WriteupsPage(){
  return <div className="editorial-page">
    <SiteHeader/>
    <main id="main-content" className="writeups-page">
      <p className="kicker"><span>01</span> Security notes</p>
      <div className="page-title-row"><h1>CTF Writeups</h1><p className="section-count">0 published</p></div>
      <section className="empty-index" aria-labelledby="writeup-status">
        <p id="writeup-status" className="empty-title">The index is open.</p>
        <p>CTF writeups will appear here as they are published.</p>
      </section>
      <Link className="text-link" href="/">← Back to portfolio</Link>
    </main>
    <footer className="site-footer"><span>Rifqy / CTF archive</span><span>2026</span></footer>
  </div>;
}
