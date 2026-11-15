export type TerrainAssistantResponse = {
  item_id: string
  model: string
  measured: {
    product: { instrument: string; mission: string; region: string; elevation_units: string; vertical_datum: string }
    statistics: { valid_pixels: number; nodata_pixels: number; minimum: number; maximum: number; mean: number; population_standard_deviation: number }
    window: {
      pixel_bounds: { col_off: number; row_off: number; width: number; height: number }
      elevation: { valid_cells: number; minimum: number | null; maximum: number | null; mean: number | null }
      slope_degrees: { valid_cells: number; minimum: number | null; maximum: number | null; mean: number | null }
      aspect_degrees_clockwise_from_north: { valid_cells: number; minimum: number | null; maximum: number | null; circular_mean: number | null }
      hillshade_0_255: { valid_cells: number; minimum: number | null; maximum: number | null; mean: number | null }
    }
    profile: { sample_count: number; valid_sample_count: number; elevation_range: number[] | null; distance_units: string } | null
    provenance: { sources: string[]; statistics_method: string; window_method: string; limitations: string[]; nodata_treatment: string }
  }
  interpretation: { summary: string; observations: string[]; limitations: string[] }
  verification_notice: string
}

const importMeta = import.meta as ImportMeta & { env?: { VITE_MARSIGHT_API_URL?: string } }
const API_BASE = (importMeta.env?.VITE_MARSIGHT_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export async function requestTerrainExplanation(input: {
  item_id: string
  profile?: { startCol: number; startRow: number; endCol: number; endRow: number }
}): Promise<TerrainAssistantResponse> {
  const body: Record<string, number | string> = { item_id: input.item_id, col_off: 0, row_off: 0, width: 32, height: 32 }
  if (input.profile) {
    body.profile_start_col = input.profile.startCol
    body.profile_start_row = input.profile.startRow
    body.profile_end_col = input.profile.endCol
    body.profile_end_row = input.profile.endRow
  }
  let response: Response
  try {
    response = await fetch(`${API_BASE}/api/assistant/terrain-summary`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error('The research assistant service could not be reached.')
  }
  if (!response.ok) {
    const errors: Record<number, string> = {
      402: 'The Claude workspace reached a billing or usage limit. Check its spending controls.',
      404: 'This dataset is not registered by the backend.',
      422: 'The terrain request was invalid. Check the selected profile coordinates.',
      429: 'The research assistant is rate-limited. Wait a minute before trying again.',
      503: 'The assistant or its approved raster is unavailable. Check backend configuration and raster status.',
      504: 'Claude did not respond before the request timed out. Try again later.',
    }
    throw new Error(errors[response.status] || `The research assistant returned an error (${response.status}).`)
  }
  return response.json() as Promise<TerrainAssistantResponse>
}
