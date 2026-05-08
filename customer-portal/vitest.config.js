import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

/**
 * Vitest config for customer-portal.
 *
 * Separate from vite.config.js because vite.config sets `base: '/portal/'`
 * (production mount path) which would confuse the test runner's module
 * resolution. Tests run with the default base.
 *
 * happy-dom over jsdom: ~3x faster cold start, fully covers our needs
 * (we don't use canvas / SVGGeometryElement features that need jsdom).
 *
 * Setup file: extends expect with jest-dom matchers (toBeInTheDocument
 * etc) — same pattern as `dashboard/vitest.config.ts`.
 */
export default defineConfig({
    plugins: [react()],
    test: {
        environment: 'happy-dom',
        globals: true,
        setupFiles: ['./vitest.setup.js'],
        include: ['src/**/*.{test,spec}.{js,jsx}'],
    },
});
