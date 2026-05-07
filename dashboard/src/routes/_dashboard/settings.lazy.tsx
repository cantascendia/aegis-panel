/**
 * /settings — Operator settings page. Wave-B3 Nilou rewrite.
 *
 * Design: PanelHead + 4 NilouCard sections
 *   1. General       — site-level config (subscription settings widget)
 *   2. Reality       — health probe interval + audit retention (placeholder rows)
 *   3. Notifications — SMTP / Telegram config (placeholder rows)
 *   4. Maintenance   — certificate / danger zone
 *
 * Preserves all existing mutations via SubscriptionSettingsWidget +
 * CertificateWidget — we do not alter form logic, only wrap in Nilou chrome.
 *
 * Gate: sudo-only — wrapped in <SudoRoute> matching original.
 */

import { type FC } from 'react'
import { createLazyFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { SudoRoute } from '@marzneshin/libs/sudo-routes'
import { CertificateWidget } from '@marzneshin/modules/settings'
import { SubscriptionSettingsWidget } from '@marzneshin/modules/settings/subscription'
import {
    NilouCard,
    NilouCardHeader,
    PanelHead,
} from '@marzneshin/common/components/nilou'

// ---------------------------------------------------------------------------
// Section gap constant
// ---------------------------------------------------------------------------

const SECTION_GAP = 20

// ---------------------------------------------------------------------------
// Settings page
// ---------------------------------------------------------------------------

export const Settings: FC = () => {
    const { t } = useTranslation()

    return (
        <>
            <PanelHead
                title={t('settings')}
                sub={t('page.settings.subtitle', 'Manage panel configuration and system behaviour.')}
            />

            {/* Card grid with 20px gap */}
            <div
                style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: SECTION_GAP,
                }}
            >
                {/* 1. General — subscription rules */}
                <NilouCard>
                    <NilouCardHeader
                        title={t('page.settings.section.general', 'General')}
                        sub={t(
                            'page.settings.section.general.sub',
                            'Subscription rules, URL prefix and update interval.',
                        )}
                    />
                    <SubscriptionSettingsWidget />
                </NilouCard>

                {/* 2. Reality — probe interval + audit retention */}
                <NilouCard>
                    <NilouCardHeader
                        title={t('page.settings.section.reality', 'Reality')}
                        sub={t(
                            'page.settings.section.reality.sub',
                            'Health probe schedule and audit log retention.',
                        )}
                    />
                    <div
                        style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 14,
                            color: 'hsl(var(--muted-foreground))',
                            fontSize: '0.9rem',
                        }}
                    >
                        <div
                            style={{
                                padding: '12px 16px',
                                borderRadius: 8,
                                background: 'hsl(var(--muted) / 0.4)',
                            }}
                        >
                            {t(
                                'page.settings.reality.placeholder',
                                'Reality probe interval and audit retention settings will appear here (backend P2).',
                            )}
                        </div>
                    </div>
                </NilouCard>

                {/* 3. Email / Notifications */}
                <NilouCard>
                    <NilouCardHeader
                        title={t('page.settings.section.notifications', 'Email / Notifications')}
                        sub={t(
                            'page.settings.section.notifications.sub',
                            'SMTP relay, Telegram bot token, and alert thresholds.',
                        )}
                    />
                    <div
                        style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 14,
                            color: 'hsl(var(--muted-foreground))',
                            fontSize: '0.9rem',
                        }}
                    >
                        <div
                            style={{
                                padding: '12px 16px',
                                borderRadius: 8,
                                background: 'hsl(var(--muted) / 0.4)',
                            }}
                        >
                            {t(
                                'page.settings.notifications.placeholder',
                                'SMTP and Telegram notification configuration will appear here (backend P2).',
                            )}
                        </div>
                    </div>
                </NilouCard>

                {/* 4. Maintenance — certificate + danger zone */}
                <NilouCard>
                    <NilouCardHeader
                        title={t('page.settings.section.maintenance', 'Maintenance')}
                        sub={t(
                            'page.settings.section.maintenance.sub',
                            'TLS certificate and database maintenance operations.',
                        )}
                    />
                    <CertificateWidget />
                </NilouCard>
            </div>
        </>
    )
}

export const Route = createLazyFileRoute('/_dashboard/settings')({
    component: () => (
        <SudoRoute>
            <Settings />
        </SudoRoute>
    ),
})
