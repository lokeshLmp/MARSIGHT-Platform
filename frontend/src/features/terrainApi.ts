export type TerrainStatistics = {
  product: {
    item_id: string
    instrument: string
    resolution_m_per_pixel: number
    elevation_units: string
    vertical_datum: string
  }
  valid_pixels: number
  nodata_pixels: number
  minimum: number
  maximum: number
  mean: number
  population_standard_deviation: number
  provenance: { processed_at: string; method: string; limitations: string[] }
}

export type ElevationProfile = {
  samples: { column: number; row: number; distance_crs_units: number; elevation: number | null }[]
  provenance: { processed_at: string; method: string; limitations: string[] }
}

const env = import.meta as ImportMeta & { env?: { VITE_MARSIGHT_API_URL?: string } }
const API_BASE = (env.env?.VITE_MARSIGHT_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const PRODUCT_ID = 'DTEPD_076532_0920_076203_0920_A01'

async function get<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' } })
  } catch {
    throw new Error('The MARSIGHT processing service could not be reached.')
  }
  if (!response.ok) {
    if (response.status === 503) throw new Error('The approved raster is not configured or is unavailable on the backend.')
    if (response.status === 404) throw new Error('This product is not registered by the backend.')
    if (response.status === 422) throw new Error('The processing request was rejected. Check the pixel coordinates.')
    throw new Error(`The processing service returned an error (${response.status}).`)
  }
  return response.json() as Promise<T>
}

export function getTerrainStatistics(): Promise<TerrainStatistics> {
  return get(`/api/v1/dtm/${PRODUCT_ID}/statistics`)
}

export function getElevationProfile(startCol: number, startRow: number, endCol: number, endRow: number): Promise<ElevationProfile> {
  const query = new URLSearchParams({
    start_col: String(startCol), start_row: String(startRow), end_col: String(endCol), end_row: String(endRow), samples: '128',
  })
  return get(`/api/v1/dtm/${PRODUCT_ID}/profile?${query.toString()}`)
}
