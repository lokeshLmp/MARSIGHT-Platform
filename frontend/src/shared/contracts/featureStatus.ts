export type FeatureState = 'IMPLEMENTED' | 'EXPERIMENTAL' | 'MOCK' | 'PLANNED'
export type DataState = 'connected' | 'sample' | 'not_connected' | 'unknown'

export interface FeatureStatus {
  id: string
  label: string
  state: FeatureState
  dataState: DataState
  description: string
  source?: { label: string; url: string; retrievedAt?: string }
  limitations: string[]
}

export const featureStatuses: FeatureStatus[] = [
  {
    id: 'planetary-map', label: 'Planetary map', state: 'EXPERIMENTAL', dataState: 'connected',
    description: 'The overview globe requests the Viking VIS global color mosaic through NASA Mars Trek.',
    source: { label: 'NASA Mars Trek', url: 'https://trek.nasa.gov/mars/' },
    limitations: ['This is a global color mosaic, not a HiRISE terrain raster.', 'The Terrain Explorer map surface is illustrative and does not render DTM pixels.'],
  },
  {
    id: 'dataset-discovery', label: 'Dataset discovery', state: 'IMPLEMENTED', dataState: 'unknown',
    description: 'The FastAPI service can query the USGS Mars STAC catalogue and read approved DTM header metadata when the API and source are available.',
    source: { label: 'USGS Astrogeology STAC', url: 'https://stac.astrogeology.usgs.gov/' },
    limitations: ['Catalogue results depend on USGS service availability.', 'Header metadata is not raster pixel analysis.'],
  },
  {
    id: 'terrain-analysis', label: 'Terrain analysis', state: 'IMPLEMENTED', dataState: 'unknown',
    description: 'The API implements NoData-aware statistics, bounded terrain windows, and elevation profiles for one registered HiRISE product when its real raster is configured on the server.',
    source: { label: 'USGS Mars HiRISE DTM', url: 'https://stac.astrogeology.usgs.gov/docs/data/mars/hirise_dtms/' },
    limitations: ['The raster is not bundled; live results require a configured server-side file.', 'The registered product is a regional DTM, not a global elevation model.', 'These calculations do not establish route safety or mission suitability.'],
  },
  {
    id: 'route-planning', label: 'Route planning', state: 'MOCK', dataState: 'not_connected',
    description: 'Waypoint sketching is available as a local interface mockup only.',
    limitations: ['No route distance, terrain cost, or safety rating is calculated.'],
  },
  {
    id: 'mission-assistant', label: 'Research assistant', state: 'PLANNED', dataState: 'not_connected',
    description: 'An evidence-grounded assistant is not connected.',
    limitations: ['No generated scientific recommendations are shown.'],
  },
]
