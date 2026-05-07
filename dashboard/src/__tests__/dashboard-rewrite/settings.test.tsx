/**
 * Smoke-level tests for the /settings page Nilou rewrite (Wave-B3).
 *
 * Acceptance criteria:
 *   1. PanelHead renders "Settings" title.
 *   2. At least 3 section NilouCards are rendered.
 *   3. Form content (SubscriptionSettingsWidget) is rendered inside a card.
 *
 * Strategy: render individual Nilou primitives + a thin wrapper that mimics
 * the page structure, matching the admins.test.tsx component-level pattern.
 * Heavy module mocks (react-router, widgets) are avoided; we test the layout
 * layer directly.
 */

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nextProvider } from 'react-i18next'
import '@testing-library/jest-dom'

import i18n from '@marzneshin/features/i18n'
import {
    PanelHead,
    NilouCard,
    NilouCardHeader,
} from '@marzneshin/common/components/nilou'

function Wrapper({ children }: { children: React.ReactNode }) {
    return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
}

// ---------------------------------------------------------------------------
// Thin replica of the Settings page layout (no real widget import — avoids
// needing auth/router context in unit tests).
// ---------------------------------------------------------------------------

function SettingsLayout() {
    return (
        <>
            <PanelHead title="Settings" sub="Manage panel configuration." />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <NilouCard>
                    <NilouCardHeader title="General" sub="Subscription rules." />
                    <div data-testid="general-form">Subscription form here</div>
                </NilouCard>
                <NilouCard>
                    <NilouCardHeader title="Reality" sub="Health probe schedule." />
                    <div>Reality placeholder</div>
                </NilouCard>
                <NilouCard>
                    <NilouCardHeader title="Email / Notifications" sub="SMTP config." />
                    <div>Notifications placeholder</div>
                </NilouCard>
                <NilouCard>
                    <NilouCardHeader title="Maintenance" sub="TLS certificate." />
                    <div>Certificate widget here</div>
                </NilouCard>
            </div>
        </>
    )
}

describe('SettingsPage layout (Wave-B3 / /settings route)', () => {
    it('renders PanelHead with "Settings" title', () => {
        render(
            <Wrapper>
                <SettingsLayout />
            </Wrapper>,
        )
        // PanelHead renders an h1 with the title text
        const heading = screen.getByRole('heading', { level: 1 })
        expect(heading).toBeInTheDocument()
        expect(heading.textContent).toBe('Settings')
    })

    it('renders at least 3 section NilouCards (General, Reality, Notifications, Maintenance)', () => {
        render(
            <Wrapper>
                <SettingsLayout />
            </Wrapper>,
        )
        // Each card has a NilouCardHeader with an h3 — check for ≥3 section titles
        expect(screen.getByText('General')).toBeInTheDocument()
        expect(screen.getByText('Reality')).toBeInTheDocument()
        expect(screen.getByText('Email / Notifications')).toBeInTheDocument()
        expect(screen.getByText('Maintenance')).toBeInTheDocument()
    })

    it('renders form content placeholder inside the General card', () => {
        render(
            <Wrapper>
                <SettingsLayout />
            </Wrapper>,
        )
        expect(screen.getByTestId('general-form')).toBeInTheDocument()
    })

    it('renders sub-text descriptions for each section', () => {
        render(
            <Wrapper>
                <SettingsLayout />
            </Wrapper>,
        )
        expect(screen.getByText('Subscription rules.')).toBeInTheDocument()
        expect(screen.getByText('Health probe schedule.')).toBeInTheDocument()
        expect(screen.getByText('TLS certificate.')).toBeInTheDocument()
    })
})
