import SiteHeader from '@/components/SiteHeader';
import {profile,work} from '@/lib/site-content';

export default function PortfolioPage(){
  return <div className="editorial-page">
    <SiteHeader/>
    <main id="main-content">
      <section className="portfolio-hero" aria-labelledby="portfolio-title">
        <p className="kicker"><span>00</span> Portfolio / 2026</p>
        <div className="hero-grid">
          <h1 id="portfolio-title">{profile.name}</h1>
          <div className="hero-copy"><p className="role-line">{profile.role}</p><p>{profile.introduction}</p></div>
        </div>
      </section>
      <section className="work-section" aria-labelledby="selected-work">
        <div className="section-heading">
          <p className="kicker"><span>01</span> Selected work</p>
          <p className="section-count">{String(work.length).padStart(2,'0')} entries</p>
        </div>
        <h2 id="selected-work" className="sr-only">Selected work</h2>
        <ol className="work-index">{work.map(item=><li key={item.index}>
          <a href={item.href} className="work-link">
            <span className="work-number">{item.index}</span><span className="work-title">{item.title}</span>
            <span className="work-description">{item.description}</span><span className="work-arrow" aria-hidden="true">{item.external?'↗':'→'}</span>
          </a>
        </li>)}</ol>
      </section>
    </main>
    <footer className="site-footer"><span>Based in Indonesia</span><span>Learning in public</span></footer>
  </div>;
}
