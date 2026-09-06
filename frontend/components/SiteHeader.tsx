import Link from 'next/link';

export default function SiteHeader(){
  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="site-header">
      <Link className="site-mark" href="/" aria-label="Rifqy portfolio home">
        <span>RIFQY</span><span className="site-mark-detail">NETWORKS / SECURITY</span>
      </Link>
      <nav className="site-nav" aria-label="Primary">
        <Link href="/">Index</Link><Link href="/writeups">CTF Writeups</Link>
        <a href="https://quiz.email2.my.id/">CCNA Quiz ↗</a>
      </nav>
    </header>
  </>;
}
