/**
 * Vitest setup — extends `expect` with jest-dom matchers.
 *
 * Loaded once per test run (referenced from vitest.config.js).
 * Adds toBeInTheDocument / toHaveTextContent / toBeDisabled etc.
 */
import '@testing-library/jest-dom/vitest';
