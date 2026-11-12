import { featureStatuses } from '../shared/contracts/featureStatus'

const stateLabel = { available: 'Available', prototype: 'Prototype', planned: 'Planned', unavailable: 'Unavailable' } as const

export function App() {
  return <main className="mx-auto min-h-screen max-w-[1440px] px-5 py-8 md:px-10">
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-6">
      <div><p className="text-xs font-semibold tracking-[0.35em] text-cyan-300">MARSIGHT</p><p className="mt-1 text-xs text-slate-400">PLANETARY INTELLIGENCE PLATFORM</p></div>
      <span className="rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1.5 text-xs text-amber-200">Development foundation · no live data</span>
    </header>
    <section className="grid gap-10 py-12 lg:grid-cols-[1fr_0.8fr] lg:items-end">
      <div><p className="mb-4 text-xs uppercase tracking-[0.25em] text-cyan-300">Mission systems · early build</p><h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight md:text-6xl">Explore planetary terrain with evidence in view.</h1><p className="mt-5 max-w-2xl text-base leading-7 text-slate-400">A modular foundation for planetary mapping, research, and exploration planning. Features remain clearly marked until their data sources and methods are implemented.</p></div>
      <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6"><div className="flex items-center justify-between"><h2 className="font-medium">System status</h2><span className="text-xs text-slate-500">LIVE SERVICES: 0</span></div><div className="mt-5 grid grid-cols-3 gap-3">{['Data feeds', 'Validated routes', 'AI services'].map(x => <div key={x} className="rounded-xl bg-white/[0.04] p-3"><p className="text-[11px] text-slate-500">{x}</p><p className="mt-2 text-sm text-slate-300">Not connected</p></div>)}</div></div>
    </section>
    <section><div className="mb-4 flex items-end justify-between"><div><p className="text-xs uppercase tracking-[0.2em] text-slate-500">Capability register</p><h2 className="mt-2 text-xl font-medium">What this build can do</h2></div><p className="text-xs text-slate-500">Status contract · source-aware</p></div><div className="grid gap-3 md:grid-cols-3">{featureStatuses.map(feature => <article key={feature.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5"><div className="flex items-center justify-between gap-3"><h3 className="font-medium">{feature.label}</h3><span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-slate-300">{stateLabel[feature.state]}</span></div><p className="mt-3 text-sm leading-6 text-slate-400">{feature.description}</p><p className="mt-4 border-t border-white/10 pt-3 text-xs text-slate-500">{feature.limitations[0]}</p></article>)}</div></section>
    <footer className="mt-12 border-t border-white/10 py-5 text-xs text-slate-500">Interface foundation only. No operational, scientific, or safety conclusions are provided.</footer>
  </main>
}

