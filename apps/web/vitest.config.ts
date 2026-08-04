import path from 'path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Unit/integration tests for the client boundary, stores, and (later) components.
// jsdom environment + a shared setup file; globals stay off — tests import from
// 'vitest' explicitly so strict tsconfig `types` does not need widening.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
    restoreMocks: true,
    unstubEnvs: true,
  },
})
