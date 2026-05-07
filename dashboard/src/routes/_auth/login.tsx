/**
 * /login — Operator login page. Wave-B3 Nilou restyle.
 *
 * FORBIDDEN PATH: auth UI — conservative changes only.
 *   - Auth logic (useAuth, LoginForm, mutation, redirect) UNCHANGED.
 *   - Only the visual shell (Card chrome) is replaced with NilouCard.
 *   - LotusMark brand mark added above form (decorative, no logic change).
 *   - Cormorant title + sub-text added.
 *
 * Token handling, mutation and redirect-on-success live entirely inside
 * <LoginForm /> and the useAuth store — not touched here.
 */

import { createFileRoute } from '@tanstack/react-router'
import { type FC } from 'react'
import { useTranslation } from 'react-i18next'
import { LoginForm, useAuth } from '@marzneshin/modules/auth'
import {
    NilouCard,
    LotusMark,
} from '@marzneshin/common/components/nilou'

const LoginPage: FC = () => {
    const { t } = useTranslation()
    const { removeAuthToken } = useAuth()
    removeAuthToken()

    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '100vh',
                padding: '1.5rem',
                background: 'hsl(var(--background))',
            }}
        >
            <NilouCard
                style={{
                    width: '100%',
                    maxWidth: 440,
                }}
            >
                {/* Brand mark */}
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
                    <LotusMark size={48} breathe />
                </div>

                {/* Title */}
                <h1
                    style={{
                        margin: '0 0 4px',
                        fontFamily: "'Cormorant Garamond', Georgia, serif",
                        fontWeight: 500,
                        fontSize: '1.75rem',
                        color: 'hsl(var(--foreground))',
                        letterSpacing: '-0.02em',
                        textAlign: 'center',
                    }}
                >
                    {t('page.login.title', 'Welcome back')}
                </h1>

                {/* Sub-text */}
                <p
                    style={{
                        margin: '0 0 24px',
                        color: 'hsl(var(--muted-foreground))',
                        fontSize: '0.9rem',
                        textAlign: 'center',
                    }}
                >
                    {t('page.login.sub', 'Operator access')}
                </p>

                {/* Existing LoginForm — auth logic preserved as-is */}
                <LoginForm />
            </NilouCard>
        </div>
    )
}

export const Route = createFileRoute('/_auth/login')({
    component: () => <LoginPage />,
})
