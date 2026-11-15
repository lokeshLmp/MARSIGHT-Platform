# HiRISE terrain reference and calculation limits

## Supplied historical product summary

- Product: `DTEPD_076532_0920_076203_0920_A01`
- Instrument and mission: HiRISE on Mars Reconnaissance Orbiter
- Producer: University of Arizona
- Target and region: Mars, South Polar residual cap
- Raster: 2,287 × 4,969 pixels (11,364,103 total), 2 m/pixel
- Valid and NoData counts: 9,537,521 valid; 1,826,582 NoData
- Historical elevation statistics: minimum 2,908.5302734375 m; maximum 3,259 m; mean 3,116.541120762895 m; standard deviation 80.14356621471624 m
- Vertical reference: Mars 2000 Datum; the supplied PDS label states metres above the Martian equipotential surface
- CRS and NoData: the historical supplied summary did not retain the exact header CRS or NoData sentinel. Current backend validation uses the PDS product definition and records CRS linear units as unknown.
- Provenance: summary results from the complete local raster, as supplied for this product. Keep them labelled as historical reference unless a current live API response is displayed.

The original PDS label and product page are [here](https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_076500_076599/ESP_076532_0920_ESP_076203_0920/) and [here](https://www.uahirise.org/dtm/dtm.php?ID=ESP_076532_0920). The raster is not bundled in this repository.

## Processing available in this checkout

The backend provides:

- `GET /api/v1/dtm/{item_id}/statistics`: a bounded, NoData-aware scan over the registered product.
- `GET /api/v1/dtm/{item_id}/window`: a maximum 512 × 512 elevation window with Horn 3×3 slope/aspect and analytical hillshade.
- `GET /api/v1/dtm/{item_id}/profile`: nearest-pixel profile samples with raw raster CRS distances.

The registry validates the configured raster against the approved product's dimensions, type, NoData value, and pixel scale. `MARSIGHT_DTM_PATH` must point to the real raster on the API host. It is unset in the current environment, so these real-raster endpoints have not been exercised during this integration pass. Synthetic raster tests cover NoData, bounds, derivatives, and profile behavior. Do not claim current live processing until real-raster checks pass.

## Frontend calculation module

`frontend/src/features/terrainMath.ts` contains standalone tested operations over caller-provided in-memory grids. The React Terrain Explorer requests live statistics and profiles from the FastAPI API and presents errors when unavailable. The historical reference record remains separate from those API responses.

The current application does not render the HiRISE raster as a map layer, optimize a route against terrain, estimate route safety, or provide life-support guidance. The route sketch and illustrative terrain panel remain mock features. Slope/aspect use Horn derivatives with the product's 2 m/pixel map scale; projection distortion is not corrected. Profiles report raw CRS units because the raster header reports its linear unit as unknown.
