type Provenance = {
  source_organisation: string
  retrieved_at: string
  processing_method: string
  limitations: string[]
  experimental: boolean
  sources: string[]
}

export type DatasetItem = {
  item_id: string
  collection: string
  title: string | null
  acquisition_date: string | null
  acquisition_date_note: string
  mission: string | null
  instrument: string | null
  resolution_m: number | null
  resolution_note: string
  stac_item_url: string
  license: string | null
  limitations: string[]
  provenance: Provenance
}

export type DtmMetadata = {
  item_id: string
  collection: string
  title: string | null
  stac_item_url: string
  raster: {
    width: number
    height: number
    band_count: number
    dtype: string
    crs: { name: string | null; epsg: number | null; linear_unit: string | null }
    pixel_size: { x: number; y: number; unit: string | null }
    nodata: number | null
    nodata_source: string
  }
  elevation_units: { value: string | null; confirmed: boolean; note: string }
  vertical_reference: { value: string | null; confirmed: boolean; documented_reference: string | null; note: string }
  consistency_checks: string[]
  provenance: Provenance
}

export type DatasetsResponse = {
  query: { bbox: number[]; collections: string[]; limit_per_collection: number }
  collections: { collection: string; status: 'ok' | 'unavailable'; matched: number | null; returned: number; error: string | null }[]
  items: DatasetItem[]
  coverage_note: string
  provenance: Provenance
}

const importMeta = import.meta as ImportMeta & { env?: { VITE_MARSIGHT_API_URL?: string } }
const API_BASE = (importMeta.env?.VITE_MARSIGHT_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function getJson<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' } })
  } catch {
    throw new Error('The metadata service could not be reached. Start the MARSIGHT research API and try again.')
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      404: 'The requested dataset or DTM asset was not found.',
      422: 'The query was not accepted. Check the bounding box and selected collection.',
      502: 'The source metadata could not be read safely.',
      503: 'The USGS STAC source is temporarily unavailable.',
      504: 'The DTM header read timed out. Try again later.',
    }
    throw new Error(messages[response.status] || `The metadata service returned an error (${response.status}).`)
  }
  return response.json() as Promise<T>
}

export function discoverDatasets(bbox: string, collection: string): Promise<DatasetsResponse> {
  const params = new URLSearchParams({ bbox, collection, limit: '10' })
  return getJson(`/datasets?${params.toString()}`)
}

export function getDtmMetadata(item: DatasetItem): Promise<DtmMetadata> {
  return getJson(`/dtm/${encodeURIComponent(item.item_id)}/metadata?collection=${encodeURIComponent(item.collection)}`)
}
