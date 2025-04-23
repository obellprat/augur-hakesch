import { resolve } from 'path'
import inject from "@rollup/plugin-inject";

export default {
  plugins: [
          inject({   // => that should be first under plugins array
            $: 'jquery',
             jQuery: 'jquery',
         })
        ],
  root: resolve(__dirname, 'src'),
  build: {
    outDir: '../../project'
  },
  server: {
    port: 5173
  }
}