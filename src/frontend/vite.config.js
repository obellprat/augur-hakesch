import { resolve } from 'path'
import inject from "@rollup/plugin-inject";
import { defineConfig } from 'vite'
import cleanPlugin from 'vite-plugin-clean'

export default defineConfig ({
  base: "./",
  plugins: [
      inject({   // => that should be first under plugins array
            $: 'jquery',
             jQuery: 'jquery',
         }),
      cleanPlugin()
        ],
  root: resolve(__dirname, 'src'),
  build: {
    outDir: '../../api'
  },
  server: {
    port: 5173
  }
})