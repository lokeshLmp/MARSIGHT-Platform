import { cpSync, existsSync, mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  define: { CESIUM_BASE_URL: JSON.stringify('/cesium/') },
  plugins: [react(), tailwindcss(), {
    name: 'copy-cesium-browser-assets',
    configResolved(config) {
      const cesiumBuild = resolve(config.root, 'node_modules/cesium/Build/Cesium')
      const publicCesium = resolve(config.root, 'public/cesium')
      mkdirSync(publicCesium, { recursive: true })
      for (const directory of ['Assets', 'Workers', 'ThirdParty', 'Widgets']) {
        const source = resolve(cesiumBuild, directory)
        if (existsSync(source)) cpSync(source, resolve(publicCesium, directory), { recursive: true })
      }
    },
  }],
})
