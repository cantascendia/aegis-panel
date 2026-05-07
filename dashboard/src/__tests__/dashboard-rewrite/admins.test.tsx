/**
 * Smoke-level tests for the /admins page Nilou rewrite.
 *
 * Asserts:
 *   - PanelHead renders title "Admins"
 *   - KPI cards render label + value for the 3 operator KPIs
 *   - Pill renders "Sudo" / "Admin" badge text
 *   - StatusDot renders for active vs never-logged-in states
 */

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nextProvider } from 'react-i18next'
import '@testing-library/jest-dom'

import i18n from '@marzneshin/features/i18n'
import { PanelHead, KPI, Pill, StatusDot } from '@marzneshin/common/components/nilou'

function Wrapper({ children }: { children: React.ReactNode }) {
    return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
}

describe('AdminsPage layout components', () => {
    it('PanelHead renders the "Admins" title', () => {
        render(
            <Wrapper>
                <PanelHead title="Admins" />
            </Wrapper>,
        )
        expect(screen.getByText('Admins')).toBeInTheDocument()
    })

    it('KPI renders Total Admins metric', () => {
        render(
            <Wrapper>
                <KPI label="Total Admins" value={3} accent="teal" />
            </Wrapper>,
        )
        expect(screen.getByText('Total Admins')).toBeInTheDocument()
        expect(screen.getByText('3')).toBeInTheDocument()
    })

    it('KPI renders Sudo metric', () => {
        render(
            <Wrapper>
                <KPI label="Sudo" value={1} accent="gold" />
            </Wrapper>,
        )
        expect(screen.getByText('Sudo')).toBeInTheDocument()
        expect(screen.getByText('1')).toBeInTheDocument()
    })

    it('Pill renders "Sudo" role badge', () => {
        render(
            <Wrapper>
                <Pill tone="gold">Sudo</Pill>
            </Wrapper>,
        )
        const pill = screen.getByText('Sudo')
        expect(pill).toBeInTheDocument()
        // Pill is uppercase via CSS text-transform; the DOM text is still "Sudo"
        expect(pill.tagName).toBe('SPAN')
    })

    it('Pill renders "Admin" role badge', () => {
        render(
            <Wrapper>
                <Pill tone="teal">Admin</Pill>
            </Wrapper>,
        )
        expect(screen.getByText('Admin')).toBeInTheDocument()
    })

    it('StatusDot renders green for active admin', () => {
        const { container } = render(<StatusDot tone="emerald" size={8} />)
        const dot = container.querySelector('span')
        expect(dot).toBeInTheDocument()
        // JSDOM converts #5bc0be → rgb(91,192,190)
        expect(dot?.style.background).toMatch(/rgb\(91,\s*192,\s*190\)/)
    })

    it('StatusDot renders muted for never-logged-in admin', () => {
        const { container } = render(<StatusDot tone="muted" size={8} />)
        const dot = container.querySelector('span')
        expect(dot).toBeInTheDocument()
        // JSDOM converts #8a96b0 → rgb(138,150,176)
        expect(dot?.style.background).toMatch(/rgb\(138,\s*150,\s*176\)/)
    })

    it('PanelHead renders Create Admin action', () => {
        render(
            <Wrapper>
                <PanelHead
                    title="Admins"
                    actions={<button>Create Admin</button>}
                />
            </Wrapper>,
        )
        expect(screen.getByRole('button', { name: 'Create Admin' })).toBeInTheDocument()
    })
})
