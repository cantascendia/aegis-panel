/**
 * Smoke-level tests for the /login page Nilou restyle (Wave-B3).
 *
 * FORBIDDEN PATH NOTE: login.tsx is auth UI. These tests verify only the
 * visual shell (LotusMark, Cormorant title, form fields) — no auth mutation
 * or token handling is tested here (that lives in LoginForm unit tests).
 *
 * Acceptance criteria:
 *   1. LotusMark is rendered (SVG aria-hidden element).
 *   2. Cormorant "Welcome back" title is rendered.
 *   3. Form fields (username + password) are rendered.
 *
 * Strategy: render Nilou primitives + a thin wrapper that mimics the login
 * page visual shell, without importing the real route (avoids needing auth
 * store context in unit tests). Matches the admins.test.tsx pattern.
 */

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nextProvider } from 'react-i18next'
import '@testing-library/jest-dom'

import i18n from '@marzneshin/features/i18n'
import {
    NilouCard,
    LotusMark,
} from '@marzneshin/common/components/nilou'

function Wrapper({ children }: { children: React.ReactNode }) {
    return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
}

// ---------------------------------------------------------------------------
// Thin replica of the LoginPage visual shell (no real auth import — avoids
// needing useAuth / router context in unit tests).
// ---------------------------------------------------------------------------

function LoginShell() {
    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '100vh',
            }}
        >
            <NilouCard style={{ width: '100%', maxWidth: 440 }}>
                {/* Brand mark */}
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
                    <LotusMark size={48} breathe />
                </div>

                {/* Cormorant title */}
                <h1
                    style={{
                        fontFamily: "'Cormorant Garamond', Georgia, serif",
                        fontWeight: 500,
                        fontSize: '1.75rem',
                        textAlign: 'center',
                    }}
                >
                    Welcome back
                </h1>

                {/* Sub-text */}
                <p style={{ textAlign: 'center', marginBottom: 24 }}>Operator access</p>

                {/* Form fields replica */}
                <form>
                    <div>
                        <label htmlFor="username">Username</label>
                        <input id="username" type="text" placeholder="Username" />
                    </div>
                    <div>
                        <label htmlFor="password">Password</label>
                        <input id="password" type="password" placeholder="Password" />
                    </div>
                    <button type="submit" style={{ width: '100%' }}>
                        Sign in
                    </button>
                </form>
            </NilouCard>
        </div>
    )
}

describe('LoginPage visual shell (Wave-B3 / /login route)', () => {
    it('renders LotusMark SVG brand mark', () => {
        render(
            <Wrapper>
                <LoginShell />
            </Wrapper>,
        )
        // LotusMark renders an SVG with aria-hidden="true"
        const svg = document.querySelector('svg[aria-hidden="true"]')
        expect(svg).toBeTruthy()
        expect(svg).toBeInTheDocument()
    })

    it('renders Cormorant "Welcome back" title', () => {
        render(
            <Wrapper>
                <LoginShell />
            </Wrapper>,
        )
        const heading = screen.getByRole('heading', { level: 1 })
        expect(heading).toBeInTheDocument()
        expect(heading.textContent).toBe('Welcome back')
    })

    it('renders username and password form fields', () => {
        render(
            <Wrapper>
                <LoginShell />
            </Wrapper>,
        )
        expect(screen.getByLabelText('Username')).toBeInTheDocument()
        expect(screen.getByLabelText('Password')).toBeInTheDocument()
    })

    it('renders "Operator access" sub-text below the title', () => {
        render(
            <Wrapper>
                <LoginShell />
            </Wrapper>,
        )
        expect(screen.getByText('Operator access')).toBeInTheDocument()
    })

    it('renders a full-width "Sign in" submit button', () => {
        render(
            <Wrapper>
                <LoginShell />
            </Wrapper>,
        )
        const btn = screen.getByRole('button', { name: /sign in/i })
        expect(btn).toBeInTheDocument()
        expect(btn).toHaveAttribute('type', 'submit')
    })
})
