/**
 * Canonical, supplied reference record for one HiRISE product. The frontend
 * does not read the raster or calculate these full-raster statistics.
 */
export type HiRiseDtmReference = {
  recordStatus: 'SUPPLIED_REFERENCE_NOT_LIVE'
  product: {
    productId: string
    stereoProductId: string
    collection: string
    productType: string
    instrument: string
    mission: string
    producer: string
    target: string
    region: string
  }
  raster: {
    columns: number
    rows: number
    bands: number
    dataType: 'float32'
    totalPixels: number
    validPixels: number
    noDataPixels: number
    pdsMapScaleMetersPerPixel: number
    headerPixelSizeMetersApprox: number
    headerPixelSizeSource: string
  }
  projection: {
    name: 'Polar stereographic'
    latitudeType: 'Planetocentric'
    positiveLongitudeDirection: 'East'
    centerLatitudeDegrees: number
    centerLongitudeDegrees: number
    marsRadiiKilometers: { a: number; b: number; c: number }
    headerCrsWktStatus: string
    epsg: null
  }
  elevation: {
    units: 'm'
    verticalDatum: 'Mars 2000 Datum'
    verticalReference: string
  }
  noData: {
    pdsBitPattern: '16#FF7FFFFB#'
    float32ValueApprox: number
    interpretation: string
  }
  statistics: {
    status: 'SUPPLIED_REFERENCE_NOT_LIVE'
    minimumMeters: number
    maximumMeters: number
    meanMetersApprox: number
    standardDeviationMetersApprox: number
    sourceAndMethod: string
  }
  provenance: {
    pdsProductDirectory: string
    hiriseProductPage: string
    metadataSources: string[]
    retrievedAt: null
    retrievedAtNote: string
  }
  limitations: string[]
}

export const hiriseDtmReference: HiRiseDtmReference = {
  recordStatus: 'SUPPLIED_REFERENCE_NOT_LIVE',
  product: {
    productId: 'DTEPD_076532_0920_076203_0920_A01',
    stereoProductId: 'ESP_076532_0920_ESP_076203_0920',
    collection: 'mro_hirise_socet_dtms',
    productType: 'HiRISE stereo digital terrain model',
    instrument: 'HiRISE',
    mission: 'Mars Reconnaissance Orbiter',
    producer: 'University of Arizona',
    target: 'Mars',
    region: 'South Polar residual cap',
  },
  raster: {
    columns: 2287,
    rows: 4969,
    bands: 1,
    dataType: 'float32',
    totalPixels: 11_364_103,
    validPixels: 9_537_521,
    noDataPixels: 1_826_582,
    pdsMapScaleMetersPerPixel: 2,
    headerPixelSizeMetersApprox: 2.01184,
    headerPixelSizeSource: 'Previously inspected STAC/GeoTIFF header metadata; approximate value.',
  },
  projection: {
    name: 'Polar stereographic',
    latitudeType: 'Planetocentric',
    positiveLongitudeDirection: 'East',
    centerLatitudeDegrees: -90,
    centerLongitudeDegrees: 0,
    marsRadiiKilometers: { a: 3396.19, b: 3396.19, c: 3376.2 },
    headerCrsWktStatus: 'A CRS WKT was reported by prior header inspection; the exact WKT text is not retained in this reference.',
    epsg: null,
  },
  elevation: {
    units: 'm',
    verticalDatum: 'Mars 2000 Datum',
    verticalReference: 'The PDS label states elevations are metres above the Martian equipotential surface.',
  },
  noData: {
    pdsBitPattern: '16#FF7FFFFB#',
    float32ValueApprox: -3.4028226550889045e38,
    interpretation: 'PDS label MISSING_CONSTANT; exclude this float32 value from valid-data statistics.',
  },
  statistics: {
    status: 'SUPPLIED_REFERENCE_NOT_LIVE',
    minimumMeters: 2908.5302734375,
    maximumMeters: 3259,
    meanMetersApprox: 3116.541120763,
    standardDeviationMetersApprox: 80.1435662147,
    sourceAndMethod: 'Previously supplied or independently inspected full-raster statistics. Neither the frontend nor the included health-only backend calculates them.',
  },
  provenance: {
    pdsProductDirectory: 'https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_076500_076599/ESP_076532_0920_ESP_076203_0920/',
    hiriseProductPage: 'https://www.uahirise.org/dtm/dtm.php?ID=ESP_076532_0920',
    metadataSources: [
      'PDS product label: dimensions, sample type, map scale, projection parameters, NoData bit pattern, elevation units, and vertical reference.',
      'Previously inspected STAC/GeoTIFF header metadata: approximate pixel size and presence of CRS WKT.',
      'Previously supplied or independently inspected full-raster summary: valid/NoData counts and elevation statistics.',
    ],
    retrievedAt: null,
    retrievedAtNote: 'No retrieval timestamp is available for this static reference record.',
  },
  limitations: [
    'The raster pixels are not bundled, read, visualized, or processed by this frontend or the included health-only backend.',
    'PDS MAP_SCALE (2 m/pixel) and the approximate STAC/GeoTIFF header pixel size (~2.01184 m) are preserved as separate source values; their difference is not resolved or attributed here.',
    'The exact header CRS WKT was not retained; no EPSG identifier is asserted.',
    'The supplied statistics describe this product only and are not live backend results.',
    'The terrain surface and route sketch remain illustrative mocks; no route cost, distance, or safety assessment is calculated.',
  ],
}

if (hiriseDtmReference.raster.columns * hiriseDtmReference.raster.rows !== hiriseDtmReference.raster.totalPixels
  || hiriseDtmReference.raster.validPixels + hiriseDtmReference.raster.noDataPixels !== hiriseDtmReference.raster.totalPixels) {
  throw new Error('HiRISE reference pixel counts do not match the raster dimensions.')
}
