/**
 * Smoke-level tests for the /users page Nilou rewrite.
 *
 * The page is a route-level lazy component that composes:
 *   - PanelHead with title "Users"
 *   - KPI grid (4 cards from useUsersStatsQuery)
 *   - NilouCard wrapping UsersTable
 *
 * We render PanelHead + KPI in isolation (no router / react-query needed)
 * and assert the key layout is wired correctly.
 *
 * Integration of UsersTable itself (EntityTable + real query) is not
 * tested here — those concerns live in the module tests.
 */

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nextProvider } from 'react-i18next'
import '@testing-library/jest-dom'

import i18n from '@marzneshin/features/i18n'
import { PanelHead } from '@marzneshin/common/components/nilou'
import { KPI } from '@marzneshin/common/components/nilou'
import { StatusDot } from '@marzneshin/common/components/nilou'

function Wrapper({ children }: { children: React.ReactNode }) {
    return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
}

describe('UsersPage layout components', () => {
    it('PanelHead renders the "Users" title', () => {
        render(
            <Wrapper>
                <PanelHead title="Users" sub="142 customers · 98 active" />
            </Wrapper>,
        )
        expect(screen.getByText('Users')).toBeInTheDocument()
        expect(screen.getByText('142 customers · 98 active')).toBeInTheDocument()
    })

    it('KPI renders its label and value for Total metric', () => {
        render(
            <Wrapper>
                <KPI label="Total" value={142} accent="teal" />
            </Wrapper>,
        )
        expect(screen.getByText('Total')).toBeInTheDocument()
        expect(screen.getByText('142')).toBeInTheDocument()
    })

    it('KPI renders Active metric', () => {
        render(
            <Wrapper>
                <KPI label="Active" value={98} accent="emerald" />
            </Wrapper>,
        )
        expect(screen.getByText('Active')).toBeInTheDocument()
        expect(screen.getByText('98')).toBeInTheDocument()
    })

    it('KPI renders Expiring metric with coral accent', () => {
        render(
            <Wrapper>
                <KPI label="Expiring (7d)" value={5} accent="coral" />
            </Wrapper>,
        )
        expect(screen.getByText('Expiring (7d)')).toBeInTheDocument()
        expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('StatusDot renders for active user (emerald tone)', () => {
        const { container } = render(<StatusDot tone="emerald" size={8} />)
        const dot = container.querySelector('span')
        expect(dot).toBeInTheDocument()
        // JSDOM converts #5bc0be → rgb(91,192,190); match the rgb form
        expect(dot?.style.background).toMatch(/rgb\(91,\s*192,\s*190\)/)
    })

    it('StatusDot renders for inactive user (muted tone)', () => {
        const { container } = render(<StatusDot tone="muted" size={8} />)
        const dot = container.querySelector('span')
        expect(dot).toBeInTheDocument()
        // JSDOM converts #8a96b0 → rgb(138,150,176)
        expect(dot?.style.background).toMatch(/rgb\(138,\s*150,\s*176\)/)
    })

    it('PanelHead renders action button text', () => {
        render(
            <Wrapper>
                <PanelHead title="Users" actions={<button>Add User</button>} />
            </Wrapper>,
        )
        expect(screen.getByRole('button', { name: 'Add User' })).toBeInTheDocument()
    })
})
