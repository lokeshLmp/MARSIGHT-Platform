export type TerrainGrid = {
  width: number
  height: number
  values: ArrayLike<number>
  noData: number | null
  pixelSizeX: number
  pixelSizeY: number
}

export type TerrainStatistics = {
  count: number
  noDataCount: number
  min: number | null
  max: number | null
  mean: number | null
  standardDeviation: number | null
}

export type TerrainProducts = {
  slopeDegrees: Float32Array
  aspectDegrees: Float32Array
  hillshade: Float32Array
  valid: Uint8Array
}

function isValid(value: number, noData: number | null): boolean {
  return Number.isFinite(value) && (noData == null || value !== noData)
}

function validateGrid(grid: TerrainGrid): void {
  if (!Number.isInteger(grid.width) || !Number.isInteger(grid.height) || grid.width < 1 || grid.height < 1) {
    throw new RangeError('Grid width and height must be positive integers.')
  }
  if (grid.values.length !== grid.width * grid.height) {
    throw new RangeError('Grid value count must equal width × height.')
  }
  if (!Number.isFinite(grid.pixelSizeX) || !Number.isFinite(grid.pixelSizeY) || grid.pixelSizeX <= 0 || grid.pixelSizeY <= 0) {
    throw new RangeError('Pixel sizes must be finite positive values in the same linear unit.')
  }
}

export function calculateTerrainStatistics(values: ArrayLike<number>, noData: number | null): TerrainStatistics {
  let count = 0
  let noDataCount = 0
  let mean = 0
  let sumSquaredDifferences = 0
  let min = Infinity
  let max = -Infinity

  for (let index = 0; index < values.length; index += 1) {
    const value = values[index]
    if (!isValid(value, noData)) {
      noDataCount += 1
      continue
    }
    count += 1
    const delta = value - mean
    mean += delta / count
    sumSquaredDifferences += delta * (value - mean)
    min = Math.min(min, value)
    max = Math.max(max, value)
  }

  return {
    count,
    noDataCount,
    min: count ? min : null,
    max: count ? max : null,
    mean: count ? mean : null,
    standardDeviation: count ? Math.sqrt(sumSquaredDifferences / count) : null,
  }
}

/** Horn 3×3 derivatives. Outputs are NaN wherever a complete valid neighbourhood is unavailable. */
export function deriveTerrainProducts(grid: TerrainGrid, sunAzimuthDegrees = 315, sunAltitudeDegrees = 45): TerrainProducts {
  validateGrid(grid)
  if (!Number.isFinite(sunAzimuthDegrees) || !Number.isFinite(sunAltitudeDegrees) || sunAltitudeDegrees <= 0 || sunAltitudeDegrees > 90) {
    throw new RangeError('Sun azimuth must be finite and sun altitude must be in (0, 90] degrees.')
  }

  const length = grid.width * grid.height
  const slopeDegrees = new Float32Array(length).fill(Number.NaN)
  const aspectDegrees = new Float32Array(length).fill(Number.NaN)
  const hillshade = new Float32Array(length).fill(Number.NaN)
  const valid = new Uint8Array(length)
  const azimuth = sunAzimuthDegrees * Math.PI / 180
  const altitude = sunAltitudeDegrees * Math.PI / 180
  const sunEast = Math.cos(altitude) * Math.sin(azimuth)
  const sunNorth = Math.cos(altitude) * Math.cos(azimuth)
  const sunUp = Math.sin(altitude)

  for (let row = 1; row < grid.height - 1; row += 1) {
    for (let column = 1; column < grid.width - 1; column += 1) {
      const index = row * grid.width + column
      const a = grid.values[index - grid.width - 1]
      const b = grid.values[index - grid.width]
      const c = grid.values[index - grid.width + 1]
      const d = grid.values[index - 1]
      const f = grid.values[index + 1]
      const g = grid.values[index + grid.width - 1]
      const h = grid.values[index + grid.width]
      const i = grid.values[index + grid.width + 1]
      if (!isValid(a, grid.noData) || !isValid(b, grid.noData) || !isValid(c, grid.noData)
        || !isValid(d, grid.noData) || !isValid(grid.values[index], grid.noData) || !isValid(f, grid.noData)
        || !isValid(g, grid.noData) || !isValid(h, grid.noData) || !isValid(i, grid.noData)) continue

      const dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * grid.pixelSizeX)
      // Raster row indices increase downward; negate the row derivative to obtain north-positive dz/dy.
      const dzdy = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * grid.pixelSizeY)
      const slope = Math.atan(Math.hypot(dzdx, dzdy))
      const aspect = (Math.atan2(-dzdx, -dzdy) * 180 / Math.PI + 360) % 360
      const illumination = (-dzdx * sunEast - dzdy * sunNorth + sunUp) / Math.sqrt(1 + dzdx * dzdx + dzdy * dzdy)

      slopeDegrees[index] = slope * 180 / Math.PI
      aspectDegrees[index] = Math.hypot(dzdx, dzdy) === 0 ? 0 : aspect
      hillshade[index] = Math.max(0, Math.min(255, Math.round(255 * illumination)))
      valid[index] = 1
    }
  }

  return { slopeDegrees, aspectDegrees, hillshade, valid }
}

export type ProfileSample = { distance: number; elevation: number | null; column: number; row: number }

/** Samples a straight profile between pixel-centre coordinates, retaining NoData gaps as nulls. */
export function sampleElevationProfile(
  grid: TerrainGrid,
  start: { column: number; row: number },
  end: { column: number; row: number },
  requestedSamples?: number,
): ProfileSample[] {
  validateGrid(grid)
  const values = [start.column, start.row, end.column, end.row]
  if (!values.every(Number.isFinite)) throw new RangeError('Profile endpoints must be finite pixel coordinates.')
  const deltaColumn = end.column - start.column
  const deltaRow = end.row - start.row
  const length = Math.hypot(deltaColumn * grid.pixelSizeX, deltaRow * grid.pixelSizeY)
  const sampleCount = requestedSamples ?? Math.max(2, Math.ceil(Math.hypot(deltaColumn, deltaRow)) + 1)
  if (!Number.isInteger(sampleCount) || sampleCount < 2 || sampleCount > 10000) throw new RangeError('Profile sample count must be an integer from 2 to 10000.')

  return Array.from({ length: sampleCount }, (_, index) => {
    const t = index / (sampleCount - 1)
    const column = Math.round(start.column + deltaColumn * t)
    const row = Math.round(start.row + deltaRow * t)
    const inside = column >= 0 && column < grid.width && row >= 0 && row < grid.height
    const elevation = inside ? grid.values[row * grid.width + column] : Number.NaN
    return { distance: length * t, elevation: inside && isValid(elevation, grid.noData) ? elevation : null, column, row }
  })
}
