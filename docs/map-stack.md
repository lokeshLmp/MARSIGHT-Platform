# Map engine decision

## Decision: CesiumJS for the initial planetary map adapter

Validated against the official CesiumJS reference documentation on 2026-11-13. Cesium describes ellipsoids as representations of planetary bodies, provides `Ellipsoid.MARS` and `Ellipsoid.MOON`, and allows a globe to be constructed with a selected ellipsoid. The scene also accepts an ellipsoid for its geographic projection.

- [Cesium Ellipsoid API](https://cesium.com/learn/cesiumjs/ref-doc/Ellipsoid.html)
- [Cesium Globe API](https://cesium.com/learn/cesiumjs/ref-doc/Globe.html)
- [Cesium Scene API](https://cesium.com/learn/cesiumjs/ref-doc/Scene.html)

## What this validates

The engine can represent the shape and coordinate context of Mars or the Moon. This is sufficient to select CesiumJS as the frontend map adapter foundation.

## What this does not validate

This does not validate a specific basemap, image/elevation tile service, dataset license, coordinate convention, registration accuracy, level of detail, route algorithm, or scientific fitness for mission operations. Those require source-by-source review and test data. No remote imagery or NASA service is connected in the starter.

## Integration boundary

Keep map rendering behind a `PlanetaryMap` feature adapter. Pass body identity, geodetic coordinates, layer metadata, and provenance through typed contracts. Use Mars or Moon ellipsoids explicitly; never silently apply WGS84 to another body. The CesiumJS package is included as the selected engine foundation; connect actual layers only after a source-specific review.


