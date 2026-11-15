import { useEffect, useRef, useState } from 'react'
import {
  Cartesian3,
  Color,
  Ellipsoid,
  GeographicTilingScheme,
  Globe,
  UrlTemplateImageryProvider,
  Viewer,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import './mars-globe.css'

const mars = new Ellipsoid(3_396_190, 3_396_190, 3_376_200)
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function MarsGlobe() {
  const host = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'fallback'>('loading')

  useEffect(() => {
    if (!host.current) return

    let viewer: Viewer | undefined
    let frameTime = performance.now()
    let markedReady = false
    let dragging = false
    let removePreRender: (() => void) | undefined
    let removeStart: (() => void) | undefined
    let removeEnd: (() => void) | undefined
    let fallbackTimer: number | undefined
    let disposed = false

    try {
      viewer = new Viewer(host.current, {
        animation: false,
        baseLayer: false,
        baseLayerPicker: false,
        fullscreenButton: false,
        geocoder: false,
        homeButton: false,
        infoBox: false,
        navigationHelpButton: false,
        sceneModePicker: false,
        selectionIndicator: false,
        timeline: false,
        useBrowserRecommendedResolution: true,
        scene3DOnly: true,
        requestRenderMode: false,
        skyBox: false,
        skyAtmosphere: false,
        contextOptions: { webgl: { alpha: true } },
      })
      const activeViewer = viewer
      let sawTileRequests = false
      fallbackTimer = window.setTimeout(() => { if (!disposed) setStatus('fallback') }, 15_000)

      activeViewer.scene.globe = new Globe(mars)
      activeViewer.scene.globe.enableLighting = true
      activeViewer.scene.globe.showGroundAtmosphere = false
      activeViewer.scene.backgroundColor = Color.TRANSPARENT
      activeViewer.scene.screenSpaceCameraController.minimumZoomDistance = mars.maximumRadius * 1.08
      activeViewer.scene.screenSpaceCameraController.maximumZoomDistance = mars.maximumRadius * 8

      const provider = new UrlTemplateImageryProvider({
        url: 'https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg',
        tilingScheme: new GeographicTilingScheme({ ellipsoid: mars }),
        maximumLevel: 8,
        credit: 'Viking VIS Global Color Mosaic · NASA / JPL / USGS via Mars Trek',
      })
      provider.errorEvent.addEventListener(() => {
        if (!disposed) setStatus('fallback')
      })
      viewer.imageryLayers.addImageryProvider(provider)
      activeViewer.camera.setView({
        destination: Cartesian3.fromDegrees(18, 8, mars.maximumRadius * 3.25, mars),
        orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 },
      })

      const canvas = activeViewer.canvas
      const startDrag = () => { dragging = true }
      const endDrag = () => { dragging = false }
      canvas.addEventListener('pointerdown', startDrag)
      window.addEventListener('pointerup', endDrag)
      removeStart = () => canvas.removeEventListener('pointerdown', startDrag)
      removeEnd = () => window.removeEventListener('pointerup', endDrag)

      removePreRender = activeViewer.scene.preRender.addEventListener(() => {
        const now = performance.now()
        const seconds = Math.min((now - frameTime) / 1000, 0.05)
        frameTime = now
        if (!dragging && !reducedMotion()) activeViewer.camera.rotateRight(seconds * 0.035)
      })

      activeViewer.scene.globe.tileLoadProgressEvent.addEventListener((pending) => {
        if (pending > 0) sawTileRequests = true
        if (!disposed && !markedReady && sawTileRequests && pending === 0) {
          markedReady = true
          window.clearTimeout(fallbackTimer)
          setStatus('ready')
        }
      })
    } catch {
      setStatus('fallback')
    }

    return () => {
      disposed = true
      removePreRender?.()
      removeStart?.()
      removeEnd?.()
      if (fallbackTimer) window.clearTimeout(fallbackTimer)
      if (viewer && !viewer.isDestroyed()) viewer.destroy()
    }
  }, [])

  return <section className="mars-globe" aria-label="Interactive Mars globe">
    <div className="globe-heading"><span className="eyebrow">MARS · GLOBAL VIEW</span><span className={`globe-status ${status}`}><i/>{status === 'ready' ? 'VIKING GLOBAL COLOUR MOSAIC' : status === 'fallback' ? 'IMAGERY UNAVAILABLE' : 'LOADING MARS IMAGERY'}</span></div>
    <div className={`globe-stage ${status === 'fallback' ? 'fallback' : ''}`}>
      <div className="globe-halo" aria-hidden="true" />
      <div className="cesium-host" ref={host} role="img" aria-label="Interactive Mars globe using the Viking global colour mosaic. Drag to rotate or scroll to change the view." />
      {status === 'loading' && <div className="globe-loading" role="status">Loading Mars basemap…</div>}
      {status === 'fallback' && <div className="globe-unavailable" role="status">Mars imagery is temporarily unavailable.</div>}
      <div className="globe-instructions" aria-hidden="true">DRAG TO ROTATE <span>·</span> SCROLL TO ZOOM</div>
    </div>
    <p className="globe-credit">Viking VIS Global Color Mosaic · NASA / JPL / USGS via <a href="https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars" target="_blank" rel="noreferrer">Mars Trek</a></p>
  </section>
}
