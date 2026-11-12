export type FeatureState = 'available' | 'prototype' | 'planned' | 'unavailable'
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
  { id: 'planetary-map', label: 'Planetary map', state: 'planned', dataState: 'not_connected', description: 'Map engine selected; no imagery or elevation layers are connected.', limitations: ['Projection support is not dataset validation.', 'No live NASA data is displayed.'] },
  { id: 'route-planning', label: 'Route planning', state: 'planned', dataState: 'not_connected', description: 'Scientific route analysis has not been implemented.', limitations: ['No route is calculated or safety-rated.'] },
  { id: 'mission-assistant', label: 'Research assistant', state: 'planned', dataState: 'not_connected', description: 'Evidence-grounded assistant is not connected.', limitations: ['No generated scientific recommendations are shown.'] },
]

