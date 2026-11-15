import assert from 'node:assert/strict'
import test from 'node:test'
import { calculateTerrainStatistics, deriveTerrainProducts, sampleElevationProfile } from './terrainMath.ts'
import { hiriseDtmReference } from './hiriseDtmReference.ts'

test('statistics omit NoData and non-finite cells and use population standard deviation', () => {
  const result = calculateTerrainStatistics([1, 2, 3, -9999, Number.NaN, Number.POSITIVE_INFINITY], -9999)
  assert.deepEqual(result, {
    count: 3,
    noDataCount: 3,
    min: 1,
    max: 3,
    mean: 2,
    standardDeviation: Math.sqrt(2 / 3),
  })
})

test('statistics report no valid samples without inventing values', () => {
  const result = calculateTerrainStatistics([-9999, Number.NaN], -9999)
  assert.equal(result.count, 0)
  assert.equal(result.noDataCount, 2)
  assert.equal(result.min, null)
  assert.equal(result.mean, null)
})

test('Horn derivatives calculate slope, downhill aspect, and hillshade from a planar grid', () => {
  const products = deriveTerrainProducts({
    width: 3,
    height: 3,
    values: [0, 1, 2, 0, 1, 2, 0, 1, 2],
    noData: -9999,
    pixelSizeX: 1,
    pixelSizeY: 1,
  })
  const centre = 4
  assert.equal(products.valid[centre], 1)
  assert.ok(Math.abs(products.slopeDegrees[centre] - 45) < 1e-5)
  assert.ok(Math.abs(products.aspectDegrees[centre] - 270) < 1e-5)
  assert.ok(products.hillshade[centre] >= 0 && products.hillshade[centre] <= 255)
  assert.equal(products.valid[0], 0, 'edge pixels lack a full 3×3 neighbourhood')
})

test('derived layers mask neighborhoods containing NoData', () => {
  const values = new Array(25).fill(10)
  values[7] = -9999
  const products = deriveTerrainProducts({ width: 5, height: 5, values, noData: -9999, pixelSizeX: 2, pixelSizeY: 2 })
  assert.equal(products.valid[12], 0)
  assert.ok(Number.isNaN(products.slopeDegrees[12]))
  assert.ok(Number.isNaN(products.aspectDegrees[12]))
  assert.ok(Number.isNaN(products.hillshade[12]))
})

test('elevation profile preserves NoData gaps and reports distance using pixel dimensions', () => {
  const samples = sampleElevationProfile(
    { width: 3, height: 1, values: [100, -9999, 120], noData: -9999, pixelSizeX: 2, pixelSizeY: 2 },
    { column: 0, row: 0 },
    { column: 2, row: 0 },
    3,
  )
  assert.deepEqual(samples.map((sample) => sample.elevation), [100, null, 120])
  assert.deepEqual(samples.map((sample) => sample.distance), [0, 2, 4])
})

test('canonical HiRISE record preserves product, PDS and header metadata provenance', () => {
  const { product, raster, projection, elevation, noData, statistics, provenance } = hiriseDtmReference
  assert.equal(product.productId, 'DTEPD_076532_0920_076203_0920_A01')
  assert.equal(product.stereoProductId, 'ESP_076532_0920_ESP_076203_0920')
  assert.equal(product.collection, 'mro_hirise_socet_dtms')
  assert.equal(product.instrument, 'HiRISE')
  assert.equal(raster.columns, 2287)
  assert.equal(raster.rows, 4969)
  assert.equal(raster.bands, 1)
  assert.equal(raster.dataType, 'float32')
  assert.equal(raster.pdsMapScaleMetersPerPixel, 2)
  assert.equal(raster.headerPixelSizeMetersApprox, 2.01184)
  assert.notEqual(raster.pdsMapScaleMetersPerPixel, raster.headerPixelSizeMetersApprox)
  assert.equal(raster.columns * raster.rows, raster.totalPixels)
  assert.equal(raster.validPixels + raster.noDataPixels, raster.totalPixels)

  assert.equal(projection.name, 'Polar stereographic')
  assert.equal(projection.latitudeType, 'Planetocentric')
  assert.equal(projection.positiveLongitudeDirection, 'East')
  assert.equal(projection.centerLatitudeDegrees, -90)
  assert.equal(projection.centerLongitudeDegrees, 0)
  assert.deepEqual(projection.marsRadiiKilometers, { a: 3396.19, b: 3396.19, c: 3376.2 })
  assert.equal(projection.epsg, null)
  assert.equal(elevation.units, 'm')
  assert.equal(elevation.verticalDatum, 'Mars 2000 Datum')
  assert.match(elevation.verticalReference, /Martian equipotential surface/)
  assert.equal(noData.pdsBitPattern, '16#FF7FFFFB#')
  assert.equal(noData.float32ValueApprox, -3.4028226550889045e38)

  assert.equal(raster.validPixels, 9_537_521)
  assert.equal(raster.noDataPixels, 1_826_582)
  assert.equal(statistics.minimumMeters, 2908.5302734375)
  assert.equal(statistics.maximumMeters, 3259)
  assert.equal(statistics.meanMetersApprox, 3116.541120763)
  assert.equal(statistics.standardDeviationMetersApprox, 80.1435662147)
  assert.equal(statistics.status, 'SUPPLIED_REFERENCE_NOT_LIVE')
  assert.match(statistics.sourceAndMethod, /Neither the frontend nor the included health-only backend calculates them/)
  assert.equal(hiriseDtmReference.recordStatus, 'SUPPLIED_REFERENCE_NOT_LIVE')
  assert.equal(provenance.retrievedAt, null)
  assert.match(provenance.pdsProductDirectory, /hirise-pds\.lpl\.arizona\.edu/)
  assert.match(provenance.hiriseProductPage, /uahirise\.org/)
})

test('invalid grids and profile sample counts fail explicitly', () => {
  assert.throws(() => deriveTerrainProducts({ width: 2, height: 2, values: [1], noData: null, pixelSizeX: 1, pixelSizeY: 1 }), /value count/)
  assert.throws(() => sampleElevationProfile({ width: 1, height: 1, values: [1], noData: null, pixelSizeX: 1, pixelSizeY: 1 }, { column: 0, row: 0 }, { column: 0, row: 0 }, 1), /sample count/)
})
