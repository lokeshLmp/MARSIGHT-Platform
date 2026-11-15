import { lazy, Suspense, useEffect, useState } from 'react'
import { featureStatuses, type FeatureState } from '../shared/contracts/featureStatus'
import { TerrainExplorer } from '../features/TerrainExplorer'
import { ResourceCatalogue } from '../features/ResourceCatalogue'

type Theme = 'light' | 'dark' | 'system'

const themeNames: Theme[] = ['light', 'dark', 'system']
const MarsGlobe = lazy(() => import('../features/MarsGlobe').then((module) => ({ default: module.MarsGlobe })))
const stateLabel: Record<FeatureState, string> = {
  IMPLEMENTED: 'Implemented', EXPERIMENTAL: 'Experimental', MOCK: 'Mock', PLANNED: 'Planned',
}

function getSavedTheme(): Theme {
  try {
    const saved = localStorage.getItem('marsight-theme')
    return themeNames.includes(saved as Theme) ? saved as Theme : 'system'
  } catch { return 'system' }
}

function ThemeControl({ theme, onChange }: { theme: Theme; onChange: (theme: Theme) => void }) {
  return <div className="theme-control" role="group" aria-label="Color theme">
    {themeNames.map((option) => <button key={option} type="button" onClick={() => onChange(option)} aria-pressed={theme === option} title={`${option[0].toUpperCase()}${option.slice(1)} theme`}>
      {option === 'light' ? '☼' : option === 'dark' ? '☾' : '◐'}<span>{option}</span>
    </button>)}
  </div>
}

function Icon({ name }: { name: 'globe' | 'route' | 'spark' }) {
  if (name === 'globe') return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>
  if (name === 'route') return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h3a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3"/></svg>
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.5 6.5L20 12l-6.5 1.5L12 20l-1.5-6.5L4 12l6.5-2.5L12 3Z"/><path d="m19 14 .8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z"/></svg>
}

export function App() {
  const [theme, setTheme] = useState<Theme>(getSavedTheme)
  const [view, setView] = useState<'overview' | 'terrain' | 'resources'>('overview')

  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = theme
    root.style.colorScheme = theme === 'system' ? '' : theme
    try { localStorage.setItem('marsight-theme', theme) } catch { /* Theme still works for this session. */ }
  }, [theme])

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#overview" aria-label="MARSIGHT home">
        <span className="brand-mark"><span /></span><span><strong>MARSIGHT</strong><small>PLANETARY EXPLORATION</small></span>
      </a>
      <div className="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation" className="main-nav">
        {[['Overview', '⌂'], ['Terrain explorer', '◎'], ['Mission planner', '⌁'], ['Data catalogue', '▤']].map(([label, icon]) => {
          const enabled = label === 'Overview' || label === 'Terrain explorer' || label === 'Data catalogue'
          const selected = label === 'Overview' ? view === 'overview' : label === 'Data catalogue' ? view === 'resources' : label === 'Terrain explorer' && view === 'terrain'
          return <button key={label} type="button" className={`nav-item ${selected ? 'active' : ''}`} aria-current={selected ? 'page' : undefined} aria-disabled={!enabled} disabled={!enabled} title={!enabled ? 'Planned for a later build milestone' : undefined} onClick={() => { if (label === 'Overview') setView('overview'); else if (label === 'Data catalogue') setView('resources'); else if (label === 'Terrain explorer') setView('terrain') }}><span className="nav-icon">{icon}</span>{label}{!enabled && <span className="nav-soon">SOON</span>}</button>
        })}
      </nav>
      <div className="sidebar-spacer" />
      <div className="mission-card"><span className="eyebrow">MISSION WINDOW</span><strong>Exploration systems<br/>coming online</strong><span className="mission-track"><i /></span><small>Platform foundation · 01 / 04</small></div>
      <div className="sidebar-foot"><span className="status-dot"/>Development environment <span className="version">v0.1</span></div>
    </aside>

    <main id="overview" className="main-content">
      <header className="topbar"><div className="breadcrumb">MARSIGHT <span>/</span> <b>{view === 'overview' ? 'OVERVIEW' : view === 'terrain' ? 'TERRAIN EXPLORER' : 'DATA CATALOGUE'}</b></div><div className="top-actions"><span className="connection-pill connected"><i/> Mars basemap connected</span><ThemeControl theme={theme} onChange={setTheme}/></div></header>
      {view === 'terrain' ? <TerrainExplorer onBack={() => setView('overview')}/> : view === 'resources' ? <ResourceCatalogue onBack={() => setView('overview')}/> : <div className="content-wrap">
        <section className="welcome-row"><div className="welcome-message"><div className="eyebrow warm"><span className="eyebrow-line"/>MISSION CONTROL <span className="eyebrow-muted">· SOL 001</span></div><h1>See the surface<br className="desktop-break"/> differently<span className="title-period">.</span></h1><p className="welcome-copy">A new perspective on the Red Planet. Explore terrain, surface data, and mission possibilities in one place.</p></div><Suspense fallback={<div className="globe-suspense" role="status">Preparing the Mars globe…</div>}><MarsGlobe/></Suspense></section>

        <section className="mission-banner"><div className="banner-symbol"><span>✳</span></div><div className="banner-copy"><div><span className="live-tag"><i/> GLOBAL MARS BASEMAP</span><span className="banner-divider">/</span><span className="banner-meta">VIKING VIS · GLOBAL COLOR MOSAIC</span></div><h2>Your mission workspace is taking shape.</h2><p>The overview globe streams a global Mars basemap. Terrain Explorer remains illustrative; mission feeds and route analysis are not connected.</p></div><div className="banner-progress"><span>BUILD PROGRESS</span><strong>01 <small>/ 04</small></strong><div><i/></div></div></section>

        <div className="section-heading"><div><span className="eyebrow">EXPLORE THE PLATFORM</span><h2>Mission intelligence</h2></div><span className="section-note">Capability status <i>·</i> Source aware</span></div>
        <section className="feature-grid" aria-label="Platform capabilities">{featureStatuses.map((feature, index) => {
          const icons = ['globe', 'route', 'spark'] as const
          const accent = ['coral', 'blue', 'violet'][index % 3]
          return <article className="feature-card" key={feature.id}>
            <div className="feature-top"><span className={`feature-icon ${accent}`}><Icon name={icons[index % 3]}/></span><span className={`feature-status ${feature.state.toLowerCase()}`}>{stateLabel[feature.state]}</span></div>
            <h3>{feature.label === 'Planetary map' ? 'Terrain explorer' : feature.label === 'Route planning' ? 'Mission planner' : feature.label}</h3>
            <p>{feature.description}</p>
            <div className="feature-bottom"><span className="data-state"><i/> {feature.dataState === 'not_connected' ? 'No data connected' : feature.dataState === 'connected' ? 'Basemap tiles connected' : feature.dataState}</span><button type="button" className="feature-arrow" aria-label={`Open ${feature.label}`} disabled={feature.state === 'PLANNED'} title={feature.state === 'PLANNED' ? 'Planned for a later build milestone' : undefined} onClick={() => feature.id === 'planetary-map' || feature.id === 'route-planning' ? setView('terrain') : undefined}>↗</button></div>
          </article>
        })}</section>

        <section className="provenance"><span className="provenance-icon">ⓘ</span><p><strong>Built for evidence-first exploration.</strong> This interface is an independent project and is not affiliated with NASA. No live mission data, scientific analysis, route calculations, or safety assessments are currently provided.</p><span className="provenance-mark">M·</span></section>
        <footer><span>© 2026 MARSIGHT · INDEPENDENT PLANETARY EXPLORATION</span><span>BUILT WITH CURIOSITY <i>✳</i></span></footer>
      </div>}
    </main>
  </div>
}
