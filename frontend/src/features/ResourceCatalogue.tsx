import './resource-catalogue.css'
import { useState } from 'react'
import { discoverDatasets, getDtmMetadata, type DatasetItem, type DatasetsResponse, type DtmMetadata } from './resourceCatalogueApi'
import { hiriseDtmReference } from './hiriseDtmReference'

type Resource = {
  id: string
  title: string
  organization: string
  scope: string
  kind: string
  description: string
  access: string
  url: string
  reviewed: string
}

const resources: Resource[] = [
  {
    id: 'mars-trek',
    title: 'Mars Trek',
    organization: 'NASA Jet Propulsion Laboratory',
    scope: 'Mars',
    kind: 'Planetary map portal',
    description: 'The overview globe requests the Viking VIS Global Color Mosaic through Mars Trek WMTS. The separate MGS MOLA products are not the layer currently requested. The Terrain Explorer remains illustrative and does not use these tiles.',
    access: 'Global globe basemap · connected',
    url: 'https://trek.nasa.gov/mars/',
    reviewed: 'Source reviewed 13 Nov 2026',
  },
  {
    id: 'trek-wmts',
    title: 'Trek WMTS service documentation',
    organization: 'NASA Trek',
    scope: 'Mars and other bodies',
    kind: 'Service documentation',
    description: 'Explains layer capabilities, GetCapabilities metadata, tile addressing, and coverage. MARSIGHT currently requests the Viking VIS Global Color Mosaic shown on the overview globe; this is not an elevation or shaded-relief layer.',
    access: 'Technical documentation · not connected',
    url: 'https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars',
    reviewed: 'Source reviewed 13 Nov 2026',
  },
  {
    id: 'usgs-maps',
    title: 'Interactive Mars geologic maps',
    organization: 'USGS Astrogeology · NASA planetary mapping program',
    scope: 'Mars',
    kind: 'Geologic map portal',
    description: 'Standardized planetary geologic maps and interactive map resources. Open the source portal to inspect individual map products, coverage, and use conditions.',
    access: 'External map portal · not connected',
    url: 'https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars',
    reviewed: 'Source reviewed 13 Nov 2026',
  },
  {
    id: 'curiosity-route',
    title: 'Curiosity’s proposed path up Mount Sharp',
    organization: 'NASA Science',
    scope: 'Mars · Curiosity mission',
    kind: 'Route example',
    description: 'A proposed science-team path and annotated exploration regions. This is a mission-planning example, not a live rover position, route feed, or route-safety result.',
    access: 'Reference article · not a feed',
    url: 'https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/',
    reviewed: 'Source reviewed 13 Nov 2026',
  },
  {
    id: 'worldview',
    title: 'NASA Worldview',
    organization: 'NASA Earthdata',
    scope: 'Earth only',
    kind: 'Earth satellite imagery',
    description: 'Visualizes Earth observation imagery and events. Worldview is not a Mars imagery source and is not used by the Mars terrain explorer.',
    access: 'Earth imagery portal · not connected',
    url: 'https://worldview.earthdata.nasa.gov/',
    reviewed: 'Scope checked 13 Nov 2026',
  },
  {
    id: 'perseverance-gallery',
    title: 'Perseverance raw images',
    organization: 'NASA Mars 2020 mission',
    scope: 'Mars · Perseverance mission',
    kind: 'Rover image gallery',
    description: 'Official browser-based gallery of rover camera images. MARSIGHT links to the gallery; no stable, documented image feed has been connected here.',
    access: 'Official gallery · not connected',
    url: 'https://mars.nasa.gov/mars2020/multimedia/raw-images/',
    reviewed: 'Source reviewed 13 Nov 2026',
  },
]

export function ResourceCatalogue({ onBack }: { onBack: () => void }) {
  const [bbox, setBbox] = useState('76,17,79,20')
  const [collection, setCollection] = useState('all')
  const [discovery, setDiscovery] = useState<DatasetsResponse | null>(null)
  const [selected, setSelected] = useState<DatasetItem | null>(null)
  const [metadata, setMetadata] = useState<DtmMetadata | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function searchDatasets(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setDiscovery(null)
    setSelected(null)
    setMetadata(null)
    try {
      setDiscovery(await discoverDatasets(bbox.trim(), collection))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Dataset discovery failed.')
    } finally {
      setBusy(false)
    }
  }

  async function showHeader(item: DatasetItem) {
    setSelected(item)
    setMetadata(null)
    setBusy(true)
    setError(null)
    try {
      setMetadata(await getDtmMetadata(item))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Raster header metadata could not be loaded.')
    } finally {
      setBusy(false)
    }
  }

  return <div className="catalogue-page">
    <div className="catalogue-titlebar"><button className="back-link" onClick={onBack}>← <span>Mission overview</span></button><span className="catalogue-pill">SOURCE REGISTER · 06 ENTRIES</span></div>
    <div className="catalogue-heading"><span className="eyebrow warm"><span className="eyebrow-line"/>DATA PROVENANCE</span><h1>Start with the source<span className="title-period">.</span></h1><p>Official planetary resources, their scope, and what MARSIGHT can currently access.</p></div>
    <section className="catalogue-notice" aria-label="NASA affiliation and data-use notice"><span>ⓘ</span><p><strong>MARSIGHT is an independent project and is not affiliated with or endorsed by NASA.</strong> NASA does not endorse any non-U.S. Government entity and is not responsible for information contained on non-U.S. Government websites. For non-U.S. Government websites, participants must comply with any data use parameters of that specific website.</p></section>
    <section className="dataset-discovery" aria-labelledby="dataset-discovery-title">
      <div className="dataset-discovery-heading"><div><span className="eyebrow">ON-DEMAND METADATA · READ ONLY</span><h2 id="dataset-discovery-title">Find Mars DTM products</h2><p>With a compatible metadata service configured, search USGS catalogue footprints using STAC metadata only; header details are fetched only when requested.</p></div><span className="catalogue-pill">NO ELEVATION PIXELS</span></div>
      <form className="dataset-query" onSubmit={searchDatasets}>
        <label className="bbox-field">Bounding box <span>(minLon, minLat, maxLon, maxLat · degrees)</span><input value={bbox} onChange={(event) => setBbox(event.target.value)} placeholder="76,17,79,20" aria-describedby="bbox-help" required /></label>
        <label className="collection-field">Collection<select value={collection} onChange={(event) => setCollection(event.target.value)}><option value="all">HiRISE + CTX DTMs</option><option value="hirise_dtm">HiRISE DTM</option><option value="ctx_dtm">CTX DTM</option></select></label>
        <button type="submit" disabled={busy}>{busy ? 'Loading…' : 'Discover datasets'}</button>
      </form>
      <p id="bbox-help" className="dataset-help">Coordinates use east-positive longitude. Antimeridian-crossing boxes are not supported. Results are research metadata and are not validated for mission or safety use.</p>
      {error && <p className="dataset-state error" role="alert">{error}</p>}
      {busy && <p className="dataset-state" role="status">Contacting the configured metadata service…</p>}
      {discovery && <>
        <div className="dataset-result-heading"><strong>{discovery.items.length} dataset{discovery.items.length === 1 ? '' : 's'} returned</strong><span>Retrieved {new Date(discovery.provenance.retrieved_at).toLocaleString()}</span></div>
        <p className="dataset-help">{discovery.coverage_note}</p>
        {discovery.collections.some((entry) => entry.status === 'unavailable') && <p className="dataset-state error" role="status">Some collections are temporarily unavailable; the results below may be partial.</p>}
        {discovery.items.length > 0 && <div className="dataset-results">{discovery.items.map((item) => <article className="dataset-result" key={`${item.collection}:${item.item_id}`}>
          <div><h3>{item.title || item.item_id}</h3><p>{item.item_id} · {item.collection}</p><p>{[item.mission, item.instrument].filter(Boolean).join(' · ') || 'Mission or instrument not declared'}{item.resolution_m != null ? ` · ${item.resolution_m} m stated resolution` : ''}</p><small>{item.acquisition_date || 'Acquisition date not declared'} — {item.acquisition_date_note}</small></div>
          <div className="dataset-result-actions"><a href={item.stac_item_url} target="_blank" rel="noreferrer">STAC item ↗</a><button type="button" disabled={busy} onClick={() => showHeader(item)}>Read DTM header</button></div>
        </article>)}</div>}
        {selected && metadata && <section className="header-metadata" aria-label={`Raster header metadata for ${metadata.item_id}`}>
          <div className="header-metadata-title"><div><span className="eyebrow">HEADER ONLY · NO PIXEL VALUES</span><h3>{metadata.title || metadata.item_id}</h3></div><span>{metadata.provenance.experimental ? 'Experimental research metadata' : 'Metadata'}</span></div>
          <dl><div><dt>Raster</dt><dd>{metadata.raster.width} × {metadata.raster.height} · {metadata.raster.band_count} band{metadata.raster.band_count === 1 ? '' : 's'} · {metadata.raster.dtype}</dd></div><div><dt>Pixel size</dt><dd>{metadata.raster.pixel_size.x} × {metadata.raster.pixel_size.y} {metadata.raster.pixel_size.unit || '(unit not declared)'}</dd></div><div><dt>CRS</dt><dd>{metadata.raster.crs.name || 'Not declared'}{metadata.raster.crs.epsg != null ? ` · EPSG:${metadata.raster.crs.epsg}` : ''}</dd></div><div><dt>Elevation units</dt><dd>{metadata.elevation_units.confirmed ? metadata.elevation_units.value : `Unconfirmed — ${metadata.elevation_units.note}`}</dd></div><div><dt>Vertical reference</dt><dd>{metadata.vertical_reference.confirmed ? metadata.vertical_reference.value : `Unconfirmed — ${metadata.vertical_reference.note}`}</dd></div><div><dt>NoData</dt><dd>{metadata.raster.nodata ?? 'Not declared'} · {metadata.raster.nodata_source}</dd></div></dl>
          {metadata.consistency_checks.length > 0 && <ul>{metadata.consistency_checks.map((check, index) => <li key={`${index}:${check}`}>{check}</li>)}</ul>}
          <p>{metadata.provenance.processing_method} Retrieved {new Date(metadata.provenance.retrieved_at).toLocaleString()}.</p>
          <ul>{metadata.provenance.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
        </section>}
      </>}
    </section>
    <div className="catalogue-summary"><span><i className="scope-dot mars"/> Mars sources</span><span><i className="scope-dot earth"/> Earth only</span><span><i className="scope-dot status"/> 1 global basemap connected · no mission feeds</span></div>
    <section className="resource-grid" aria-label="NASA and USGS resource catalogue">{resources.map((resource) => <article className="resource-card" key={resource.id}>
      <div className="resource-meta"><span className="resource-kind">{resource.kind}</span><span className={`scope-tag ${resource.scope === 'Earth only' ? 'earth' : ''}`}>{resource.scope}</span></div>
      <h2>{resource.title}</h2><p className="resource-org">{resource.organization}</p><p className="resource-description">{resource.description}</p>
      <div className="resource-access"><span className="access-mark"/> {resource.access}</div>
      <div className="resource-foot"><span>{resource.reviewed}</span><a href={resource.url} target="_blank" rel="noreferrer">Open source <span aria-hidden="true">↗</span></a></div>
    </article>)}</section>
    <section className="header-metadata" aria-label="HiRISE reference product metadata">
      <div className="header-metadata-title"><div><span className="eyebrow">SUPPLIED PRODUCT REFERENCE · NOT LIVE</span><h3>{hiriseDtmReference.product.productId}</h3></div><span>Retrieved at: unavailable</span></div>
      <dl>
        <div><dt>Product</dt><dd>{hiriseDtmReference.product.stereoProductId} · {hiriseDtmReference.product.collection} · {hiriseDtmReference.product.instrument} · {hiriseDtmReference.product.productType}</dd></div>
        <div><dt>Raster</dt><dd>{hiriseDtmReference.raster.columns} × {hiriseDtmReference.raster.rows} · {hiriseDtmReference.raster.bands} band · {hiriseDtmReference.raster.dataType} · {hiriseDtmReference.raster.totalPixels.toLocaleString()} total pixels</dd></div>
        <div><dt>Pixel scale</dt><dd>PDS map scale: {hiriseDtmReference.raster.pdsMapScaleMetersPerPixel} m/pixel. Previously inspected header size: approximately {hiriseDtmReference.raster.headerPixelSizeMetersApprox} m/pixel. These source values are preserved separately.</dd></div>
        <div><dt>Projection</dt><dd>Mars {hiriseDtmReference.projection.name}, {hiriseDtmReference.projection.latitudeType}, east-positive; centre {hiriseDtmReference.projection.centerLatitudeDegrees}°, {hiriseDtmReference.projection.centerLongitudeDegrees}°. Radii A/B/C: {hiriseDtmReference.projection.marsRadiiKilometers.a}/{hiriseDtmReference.projection.marsRadiiKilometers.b}/{hiriseDtmReference.projection.marsRadiiKilometers.c} km. No EPSG identifier asserted.</dd></div>
        <div><dt>Elevation reference</dt><dd>{hiriseDtmReference.elevation.units} · {hiriseDtmReference.elevation.verticalDatum} · {hiriseDtmReference.elevation.verticalReference}</dd></div>
        <div><dt>NoData and coverage</dt><dd>{hiriseDtmReference.noData.pdsBitPattern} (float32 ≈ {hiriseDtmReference.noData.float32ValueApprox}); {hiriseDtmReference.raster.validPixels.toLocaleString()} valid and {hiriseDtmReference.raster.noDataPixels.toLocaleString()} NoData of {hiriseDtmReference.raster.totalPixels.toLocaleString()} pixels.</dd></div>
        <div><dt>Supplied statistics</dt><dd>Minimum {hiriseDtmReference.statistics.minimumMeters} m; maximum {hiriseDtmReference.statistics.maximumMeters} m; mean ≈ {hiriseDtmReference.statistics.meanMetersApprox} m; standard deviation ≈ {hiriseDtmReference.statistics.standardDeviationMetersApprox} m.</dd></div>
      </dl>
      <p>{hiriseDtmReference.statistics.sourceAndMethod}</p>
      <ul>{hiriseDtmReference.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      <p><a href={hiriseDtmReference.provenance.pdsProductDirectory} target="_blank" rel="noreferrer">PDS product directory ↗</a> · <a href={hiriseDtmReference.provenance.hiriseProductPage} target="_blank" rel="noreferrer">HiRISE product page ↗</a></p>
    </section>
    <footer className="catalogue-footer">Source links were reviewed on 13 November 2026. Links open the provider’s site; source terms and attribution requirements apply. The Mars Trek globe layer is streamed for display; MARSIGHT has not ingested or modified it. No mission telemetry, terrain explorer basemap, or rover feed is connected.</footer>
  </div>
}
