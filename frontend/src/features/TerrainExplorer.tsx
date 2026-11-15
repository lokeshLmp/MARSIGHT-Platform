import { useEffect, useState, type CSSProperties, type FormEvent, type KeyboardEvent, type MouseEvent } from 'react'
import './terrain-explorer.css'
import { hiriseDtmReference } from './hiriseDtmReference'
import { getElevationProfile, getTerrainStatistics, type ElevationProfile, type TerrainStatistics } from './terrainApi'
import { requestTerrainExplanation, type TerrainAssistantResponse } from './terrainAssistantApi'

type Area = { id: string; name: string; subtitle: string; center: string; accent: string }
type Point = { x: number; y: number }

const areas: Area[] = [
  { id: 'crater', name: 'Crater Highlands', subtitle: 'Illustrative study area · Mars', center: 'LOCAL GRID · 0 KM', accent: '#e88460' },
  { id: 'basin', name: 'Western Basin', subtitle: 'Illustrative study area · Mars', center: 'LOCAL GRID · 0 KM', accent: '#80a9bd' },
  { id: 'delta', name: 'Northern Rise', subtitle: 'Illustrative study area · Mars', center: 'LOCAL GRID · 0 KM', accent: '#b59ac8' },
]

export function TerrainExplorer({ onBack }: { onBack: () => void }) {
  const [liveStatistics, setLiveStatistics] = useState<TerrainStatistics | null>(null)
  const [statisticsError, setStatisticsError] = useState<string | null>(null)
  const [statisticsLoading, setStatisticsLoading] = useState(true)
  const [profile, setProfile] = useState<ElevationProfile | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profilePixels, setProfilePixels] = useState({ startCol: '0', startRow: '0', endCol: '100', endRow: '100' })
  const [assistantResult, setAssistantResult] = useState<TerrainAssistantResponse | null>(null)
  const [assistantError, setAssistantError] = useState<string | null>(null)
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [areaId, setAreaId] = useState(areas[0].id)
  const [layer, setLayer] = useState<'relief' | 'contours'>('relief')
  const [waypoints, setWaypoints] = useState<Point[]>([])
  const [showWaypoints, setShowWaypoints] = useState(true)
  const [zoom, setZoom] = useState(1)
  const area = areas.find((item) => item.id === areaId) ?? areas[0]

  useEffect(() => {
    let active = true
    getTerrainStatistics().then((result) => {
      if (active) setLiveStatistics(result)
    }).catch((error: unknown) => {
      if (active) setStatisticsError(error instanceof Error ? error.message : 'Live statistics are unavailable.')
    }).finally(() => { if (active) setStatisticsLoading(false) })
    return () => { active = false }
  }, [])

  async function requestProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setProfileLoading(true)
    setProfileError(null)
    setProfile(null)
    try {
      const coordinates = Object.values(profilePixels).map((value) => Number(value))
      if (coordinates.some((value) => !Number.isInteger(value) || value < 0)) throw new Error('Enter non-negative integer pixel coordinates.')
      setProfile(await getElevationProfile(coordinates[0], coordinates[1], coordinates[2], coordinates[3]))
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : 'The profile request failed.')
    } finally {
      setProfileLoading(false)
    }
  }

  async function explainTerrain() {
    setAssistantLoading(true)
    setAssistantError(null)
    setAssistantResult(null)
    try {
      const coordinates = profile ? Object.values(profilePixels).map(Number) : null
      setAssistantResult(await requestTerrainExplanation({
        item_id: reference.product.productId,
        profile: coordinates ? { startCol: coordinates[0], startRow: coordinates[1], endCol: coordinates[2], endRow: coordinates[3] } : undefined,
      }))
    } catch (error) {
      setAssistantError(error instanceof Error ? error.message : 'The terrain explanation could not be generated.')
    } finally {
      setAssistantLoading(false)
    }
  }

  function addWaypoint(event: MouseEvent<SVGSVGElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    const x = Math.max(8, Math.min(92, ((event.clientX - bounds.left) / bounds.width) * 100))
    const y = Math.max(8, Math.min(92, ((event.clientY - bounds.top) / bounds.height) * 100))
    setWaypoints((points) => [...points, { x, y }])
  }

  function addWaypointFromKeyboard(event: KeyboardEvent<SVGSVGElement>) {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    setWaypoints((points) => [...points, { x: 50, y: 50 }])
  }

  const line = waypoints.map((point) => `${point.x},${point.y}`).join(' ')

  const reference = hiriseDtmReference
  const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })
  const referencePercent = (count: number) => `${number.format(count / reference.raster.totalPixels * 100)}%`

  return <div className="explorer-page">
    <div className="explorer-titlebar"><button type="button" className="back-link" onClick={onBack}>← <span>Mission overview</span></button><span className="mock-pill">MOCK · ILLUSTRATIVE SURFACE</span></div>
    <div className="explorer-heading"><div><span className="eyebrow warm"><span className="eyebrow-line"/>TERRAIN EXPLORER</span><h1>Explore the surface<span className="title-period">.</span></h1><p>Supplied reference statistics are separate from live backend calculations. Raster-derived values can be requested below; the illustrative surface is not pixel-rendered.</p></div><button type="button" className="reset-route" onClick={() => setWaypoints([])} disabled={waypoints.length === 0}>Reset route</button></div>

    <section className="live-processing" aria-live="polite" aria-labelledby="live-processing-title">
      <div className="control-head"><span className="eyebrow" id="live-processing-title">BACKEND PROCESSING</span><span className={liveStatistics ? 'live-pill' : 'mock-label'}>{liveStatistics ? 'LIVE' : statisticsLoading ? 'LOADING' : 'UNAVAILABLE'}</span></div>
      {statisticsLoading && <p>Reading the registered raster in bounded windows…</p>}
      {statisticsError && <p role="status">{statisticsError} Supplied reference values below are not a substitute for a live result.</p>}
      {liveStatistics && <><p>{liveStatistics.product.item_id} · {liveStatistics.product.instrument} · {liveStatistics.product.resolution_m_per_pixel} m/pixel · {liveStatistics.product.vertical_datum}</p>
        <div className="live-stats-grid"><span>Minimum <strong>{liveStatistics.minimum.toFixed(3)} {liveStatistics.product.elevation_units}</strong></span><span>Maximum <strong>{liveStatistics.maximum.toFixed(3)} {liveStatistics.product.elevation_units}</strong></span><span>Mean <strong>{liveStatistics.mean.toFixed(3)} {liveStatistics.product.elevation_units}</strong></span><span>Population σ <strong>{liveStatistics.population_standard_deviation.toFixed(3)} {liveStatistics.product.elevation_units}</strong></span><span>Valid pixels <strong>{liveStatistics.valid_pixels.toLocaleString()}</strong></span><span>NoData pixels <strong>{liveStatistics.nodata_pixels.toLocaleString()}</strong></span></div>
        <small>Processed {new Date(liveStatistics.provenance.processed_at).toLocaleString()} · {liveStatistics.provenance.method}</small></>}
    </section>

    <section className="verified-dtm" aria-labelledby="verified-dtm-title">
      <div className="verified-dtm-heading"><div><span className="eyebrow">SUPPLIED REFERENCE · NOT LIVE</span><h2 id="verified-dtm-title">{reference.product.region}</h2><p>{reference.product.productId} · {reference.product.instrument} · {reference.product.mission} · {reference.product.producer}</p><p>{reference.product.stereoProductId} · {reference.product.collection} · {reference.product.productType}</p></div><span className="verified-pill">{reference.raster.columns} × {reference.raster.rows} · {reference.raster.bands} band · {reference.raster.dataType}</span></div>
      <div className="dtm-stats" aria-label="Supplied reference elevation statistics; not calculated by this application">
        <div><span>Minimum · reference</span><strong>{number.format(reference.statistics.minimumMeters)} m</strong></div><div><span>Maximum · reference</span><strong>{number.format(reference.statistics.maximumMeters)} m</strong></div><div><span>Mean · approximate reference</span><strong>{number.format(reference.statistics.meanMetersApprox)} m</strong></div><div><span>Std. deviation · approximate reference</span><strong>{number.format(reference.statistics.standardDeviationMetersApprox)} m</strong></div><div><span>Valid pixels · {referencePercent(reference.raster.validPixels)}</span><strong>{number.format(reference.raster.validPixels)}</strong></div><div><span>NoData pixels · {referencePercent(reference.raster.noDataPixels)}</span><strong>{number.format(reference.raster.noDataPixels)}</strong></div>
      </div>
      <div className="dtm-reference-details">
        <span>PDS map scale: <strong>{reference.raster.pdsMapScaleMetersPerPixel} m/pixel</strong> · PDS label</span>
        <span>Header pixel size: <strong>~{reference.raster.headerPixelSizeMetersApprox} m/pixel</strong> · {reference.raster.headerPixelSizeSource}</span>
        <span>Projection: <strong>Mars {reference.projection.name}</strong>; {reference.projection.latitudeType}, east-positive longitude; centre {reference.projection.centerLatitudeDegrees}° lat, {reference.projection.centerLongitudeDegrees}° lon.</span>
        <span>Mars radii: A {reference.projection.marsRadiiKilometers.a} km; B {reference.projection.marsRadiiKilometers.b} km; C {reference.projection.marsRadiiKilometers.c} km. No EPSG identifier asserted.</span>
        <span>Header CRS: {reference.projection.headerCrsWktStatus}</span>
        <span>Elevation: <strong>metres</strong>; vertical datum <strong>{reference.elevation.verticalDatum}</strong>. {reference.elevation.verticalReference}</span>
        <span>NoData: PDS bits <strong>{reference.noData.pdsBitPattern}</strong> (float32 ≈ {reference.noData.float32ValueApprox}). Valid-data counts exclude this sentinel.</span>
        <span>Reference statistics: {reference.statistics.sourceAndMethod}</span>
        <span>Retrieved at: {reference.provenance.retrievedAt ?? 'Unavailable'}.</span>
        <span>Sources: <a href={reference.provenance.pdsProductDirectory} target="_blank" rel="noreferrer">PDS product directory</a> · <a href={reference.provenance.hiriseProductPage} target="_blank" rel="noreferrer">HiRISE product page</a></span>
      </div>
      <div className="terrain-layer-status" aria-label="Terrain analysis layer availability">
        <span><b>Elevation</b><i>IMPLEMENTED · BOUNDED API</i></span><span><b>Slope · degrees</b><i>IMPLEMENTED · HORN API</i></span><span><b>Aspect</b><i>IMPLEMENTED · HORN API</i></span><span><b>Hillshade</b><i>IMPLEMENTED · ANALYTICAL API</i></span><span><b>Elevation profile</b><i>{profile ? 'LIVE · REAL SAMPLES' : 'IMPLEMENTED · REQUEST REQUIRED'}</i></span><span><b>Summary statistics</b><i className={liveStatistics ? 'verified-status' : ''}>{liveStatistics ? 'LIVE · BACKEND' : 'SUPPLIED REFERENCE · NOT LIVE'}</i></span>
      </div>
      <p className="dtm-limitations"><strong>Limitations:</strong> {reference.limitations.join(' ')}</p>
      <div className="profile-request"><div className="control-head"><span className="eyebrow">ELEVATION PROFILE</span><span className="live-pill">IMPLEMENTED · API</span></div><p>Request real nearest-pixel samples using raster column and row coordinates.</p>
        <form onSubmit={requestProfile} className="profile-form">{(['startCol', 'startRow', 'endCol', 'endRow'] as const).map((key) => <label key={key}>{key.replace(/[A-Z]/g, (letter) => ` ${letter.toLowerCase()}`)}<input type="number" min="0" step="1" value={profilePixels[key]} onChange={(event) => setProfilePixels((current) => ({ ...current, [key]: event.target.value }))}/></label>)}<button type="submit" disabled={profileLoading}>{profileLoading ? 'Sampling…' : 'Load live profile'}</button></form>
        {profileError && <p role="status">{profileError}</p>}{profile && <><p className="live-profile-meta">LIVE · {profile.samples.length} samples · distances are raw CRS units, not asserted metres · {new Date(profile.provenance.processed_at).toLocaleString()}</p><div className="live-profile-values">{profile.samples.map((sample, index) => <span key={`${sample.column}-${sample.row}-${index}`}>{sample.distance_crs_units.toFixed(1)} CRS units: {sample.elevation === null ? 'NoData' : `${sample.elevation.toFixed(2)} m`}</span>)}</div></>}
      </div>
    </section>

    <section className="terrain-assistant" aria-labelledby="terrain-assistant-title" aria-live="polite">
      <div className="control-head"><div><span className="eyebrow warm"><span className="eyebrow-line"/>OPTIONAL CLAUDE RESEARCH ASSISTANT</span><h2 id="terrain-assistant-title">Read the measured terrain</h2></div><span className="assistant-pill">USER REQUESTED · BACKEND ONLY</span></div>
      <p className="assistant-intro">Claude can explain the registered HiRISE raster’s measured statistics and a small elevation, slope, aspect and hillshade window. The illustrative surface and supplied reference figures are never sent as live measurements.</p>
      <button type="button" className="assistant-button" onClick={explainTerrain} disabled={assistantLoading}>{assistantLoading ? 'Preparing scientific context…' : 'Explain this terrain'}</button>
      <p className="assistant-verification">AI-generated interpretations require scientific verification. This is not a route-safety assessment. A real approved raster and backend Claude configuration are required.</p>
      {assistantError && <p className="assistant-error" role="status">{assistantError}</p>}
      {assistantResult && <div className="assistant-result">
        <section aria-labelledby="assistant-measured-title"><h3 id="assistant-measured-title">Measured inputs · {assistantResult.measured.product.instrument}</h3>
          <p>{assistantResult.item_id} · {assistantResult.measured.product.region} · {assistantResult.measured.product.elevation_units} · {assistantResult.measured.product.vertical_datum}</p>
          <div className="assistant-metrics"><span>Full raster mean <strong>{assistantResult.measured.statistics.mean.toFixed(2)} {assistantResult.measured.product.elevation_units}</strong></span><span>Window slope range <strong>{assistantResult.measured.window.slope_degrees.minimum?.toFixed(2) ?? 'NoData'}–{assistantResult.measured.window.slope_degrees.maximum?.toFixed(2) ?? 'NoData'}°</strong></span><span>Aspect range <strong>{assistantResult.measured.window.aspect_degrees_clockwise_from_north.minimum?.toFixed(2) ?? 'NoData'}–{assistantResult.measured.window.aspect_degrees_clockwise_from_north.maximum?.toFixed(2) ?? 'NoData'}°</strong></span><span>Hillshade range <strong>{assistantResult.measured.window.hillshade_0_255.minimum?.toFixed(0) ?? 'NoData'}–{assistantResult.measured.window.hillshade_0_255.maximum?.toFixed(0) ?? 'NoData'} / 255</strong></span><span>NoData pixels <strong>{assistantResult.measured.statistics.nodata_pixels.toLocaleString()}</strong></span><span>Analysis window <strong>{assistantResult.measured.window.pixel_bounds.width}×{assistantResult.measured.window.pixel_bounds.height} · col {assistantResult.measured.window.pixel_bounds.col_off}, row {assistantResult.measured.window.pixel_bounds.row_off}</strong></span></div>
          {assistantResult.measured.profile && <p>Profile · {assistantResult.measured.profile.valid_sample_count}/{assistantResult.measured.profile.sample_count} valid samples · elevation range {assistantResult.measured.profile.elevation_range?.map((value) => `${value.toFixed(2)} ${assistantResult.measured.product.elevation_units}`).join(' to ') ?? 'NoData'} · distances are raw raster CRS units, not asserted metres.</p>}
        </section>
        <section aria-labelledby="assistant-summary-title"><h3 id="assistant-summary-title">AI interpretation · {assistantResult.model}</h3><p>{assistantResult.interpretation.summary}</p><h4>Observations</h4><ul>{assistantResult.interpretation.observations.map((item, index) => <li key={`observation-${index}`}>{item}</li>)}</ul><h4>Limitations</h4><ul>{assistantResult.interpretation.limitations.map((item, index) => <li key={`limitation-${index}`}>{item}</li>)}</ul>
          <p className="assistant-verification">{assistantResult.verification_notice}</p><p className="assistant-sources">Sources: {assistantResult.measured.provenance.sources.join(' · ')}</p>
        </section>
      </div>}
    </section>

    <div className="mock-section-label"><span className="mock-label">MOCK</span><strong>Illustrative route-sketch prototype</strong><span>This panel is not derived from the HiRISE DTM.</span></div>

    <div className="explorer-layout">
      <section className="terrain-panel" aria-label="Illustrative Mars terrain map">
        <div className="map-toolbar"><div className="map-location"><span className="map-pin" aria-hidden="true">⌖</span><span><strong>{area.name}</strong><small>{area.subtitle}</small></span></div><div className="layer-switch" role="group" aria-label="Surface visualization"><button type="button" aria-pressed={layer === 'relief'} className={layer === 'relief' ? 'selected' : ''} onClick={() => setLayer('relief')}>Relief</button><button type="button" aria-pressed={layer === 'contours'} className={layer === 'contours' ? 'selected' : ''} onClick={() => setLayer('contours')}>Contours</button></div></div>
        <div className={`terrain-canvas ${area.id} ${layer}`} style={{ '--terrain-zoom': zoom } as CSSProperties}>
          <svg className="terrain-map" viewBox="0 0 100 100" preserveAspectRatio="none" role="button" tabIndex={0} aria-label={`Stylized mock terrain of ${area.name}. Click or press Enter to add a route waypoint.`} onClick={addWaypoint} onKeyDown={addWaypointFromKeyboard}>
              <defs>
              <radialGradient id="terrainBase"><stop offset="0" stopColor={area.accent} stopOpacity=".28"/><stop offset=".55" stopColor="#b9684b" stopOpacity=".14"/><stop offset="1" stopColor="#32221f" stopOpacity=".62"/></radialGradient>
              <pattern id="terrainGrid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="currentColor" strokeOpacity=".12" strokeWidth=".16"/></pattern>
              <filter id="soft"><feGaussianBlur stdDeviation="1.3"/></filter>
            </defs>
            <rect width="100" height="100" fill="url(#terrainBase)"/>
            <g className="landforms" filter="url(#soft)">
              <path d="M-5 20C9 8 20 18 28 12S47 5 55 18s18 14 26 5 16-8 24 0v17c-11-9-18 2-28 1s-17-12-26-6-17 16-30 8S5 39-5 43Z" fill="#e9a174" fillOpacity=".19"/>
              <path d="M-5 62c13-14 23-11 33-2s15 4 22-8 18-16 28-7 17 6 27-2v29c-10 5-17-2-27 2s-15 17-29 15S28 76 18 83 0 91-5 97Z" fill="#392725" fillOpacity=".57"/>
              <path d="M27 31c8-7 20-8 28-2s11 17 5 24-16 8-26 4-15-17-7-26Z" fill="#171b1b" fillOpacity=".28"/>
              <path d="M68 52c7-10 17-11 24-4s7 16 0 22-18 8-24 1-5-13 0-19Z" fill="#e68c65" fillOpacity=".22"/>
            </g>
            <g className="contour-lines" fill="none" stroke="#f6c9a3" strokeOpacity=".42" strokeWidth=".22">
              <path d="M-5 26C12 9 22 27 35 15S53 11 59 25s18 8 25-1 15-5 22 2"/><path d="M-5 31C12 14 23 32 36 20s17-4 23 10 18 8 25-1 15-5 22 2"/>
              <path d="M-5 70c12-15 23-8 34 1s17 3 23-10 18-11 27-3 15 4 26-2"/><path d="M-5 77c12-15 23-8 34 1s17 3 23-10 18-11 27-3 15 4 26-2"/>
              <path d="M28 33c8-9 19-10 29-4s13 18 5 27-20 9-30 3-12-17-4-26Z"/><path d="M33 36c6-6 15-7 22-2s10 13 4 19-15 7-22 2-10-13-4-19Z"/>
            </g>
            <rect width="100" height="100" fill="url(#terrainGrid)"/>
            {showWaypoints && waypoints.length > 1 && <polyline points={line} fill="none" stroke="#ffd0a7" strokeWidth=".55" strokeDasharray="1.1 1.1" vectorEffect="non-scaling-stroke"/>}
            {showWaypoints && waypoints.map((point, index) => <g key={`${point.x}-${point.y}`} transform={`translate(${point.x} ${point.y})`}><circle r="2.1" fill="#f27554" fillOpacity=".22"/><circle r=".75" fill="#fff1df" stroke="#d76b4c" strokeWidth=".45"/><text x="1.4" y="-1.2" fill="#fff1df" fontSize="2.1" fontFamily="sans-serif">{String(index + 1).padStart(2, '0')}</text></g>)}
            <g className="map-labels" fill="#f2d2b9" fontFamily="sans-serif" fontSize="2.1" letterSpacing=".45"><text x="10" y="18">NORTH RIDGE</text><text x="67" y="83">BASALT FIELD</text><text x="40" y="56">LOWLAND</text></g>
          </svg>
          <div className="map-corner-label"><i/> SIMULATED RELIEF <span>·</span> NO DATA SOURCE</div>
          <div className="map-scale"><i/><span>LOCAL GRID · ILLUSTRATIVE</span></div>
          <div className="map-zoom"><button type="button" aria-label="Zoom in" title="Zoom in" disabled={zoom >= 2} onClick={() => setZoom((value) => Math.min(2, Number((value + .25).toFixed(2))))}>+</button><button type="button" aria-label="Zoom out" title="Zoom out" disabled={zoom <= .5} onClick={() => setZoom((value) => Math.max(.5, Number((value - .25).toFixed(2))))}>−</button><small aria-live="polite">{Math.round(zoom * 100)}%</small></div>
          {waypoints.length === 0 && <button type="button" className="map-hint" onClick={() => setWaypoints([{ x: 27, y: 40 }, { x: 66, y: 60 }])}>＋ <span>Add example route</span></button>}
        </div>
        <div className="map-legend"><span><i className="legend-relief"/> Relieflike shading <b>MOCK</b></span><span><i className="legend-contour"/> Contour illustration <b>MOCK</b></span><span><i className="legend-waypoint"/> User waypoint</span></div>
      </section>

      <aside className="explorer-controls"><section className="control-card"><div className="control-head"><span className="eyebrow">STUDY AREA</span><span className="mock-label">MOCK</span></div><div className="area-list" role="group" aria-label="Study area">{areas.map((item) => <button type="button" key={item.id} className={`area-option ${item.id === areaId ? 'chosen' : ''}`} aria-pressed={item.id === areaId} onClick={() => { setAreaId(item.id); setWaypoints([]) }}><span className="area-swatch" style={{ '--swatch': item.accent } as CSSProperties}/><span><strong>{item.name}</strong><small>{item.subtitle}</small></span><span className="area-check" aria-hidden="true">{item.id === areaId ? '●' : '○'}</span></button>)}</div><p className="control-footnote">Areas and surface details are illustrative UI samples only.</p></section>
        <section className="control-card route-card"><div className="control-head"><span className="eyebrow">ROUTE SKETCH</span><span className="mock-label">MOCK</span></div><p className="route-intro">Click anywhere on the surface to place a waypoint.</p><div className="route-count" aria-live="polite"><strong>{String(waypoints.length).padStart(2, '0')}</strong><span>WAYPOINT{waypoints.length === 1 ? '' : 'S'}<small> · LOCAL SKETCH</small></span></div><div className="waypoint-list">{waypoints.length ? waypoints.map((point, index) => <div className="waypoint-row" key={`${index}-${point.x}`}><span className="waypoint-number">{String(index + 1).padStart(2, '0')}</span><span>Waypoint {index + 1}<small>Local grid · {point.x.toFixed(1)}, {point.y.toFixed(1)}</small></span><button type="button" aria-label={`Remove waypoint ${index + 1}`} onClick={() => setWaypoints((points) => points.filter((_, i) => i !== index))}>×</button></div>) : <p className="empty-route">No points placed yet. This sketch is not evaluated for terrain, distance, or safety.</p>}</div><button type="button" className="route-visibility" aria-pressed={showWaypoints} onClick={() => setShowWaypoints((value) => !value)}><span aria-hidden="true">{showWaypoints ? '◉' : '○'}</span> {showWaypoints ? 'Hide' : 'Show'} route on surface</button></section>
        <div className="explorer-notice"><span>ⓘ</span><p><strong>Research preview.</strong> No NASA imagery, elevation, coordinates, distance, or route safety data is connected. CesiumJS is selected for future planet rendering.</p></div>
      </aside>
    </div>
  </div>
}
