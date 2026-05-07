import { Loading } from '@marzneshin/common/components'
import {
    UsersNoServiceAlert,
    UsersTable,
    useUsersStatsQuery,
} from '@marzneshin/modules/users'
import {
    KPI,
    NilouCard,
    PanelHead,
} from '@marzneshin/common/components/nilou'
import { createLazyFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import { type FC, Suspense } from 'react'
import { useTranslation } from 'react-i18next'

/** KPI row spanning 4 metrics from /system/stats/users */
const UsersKPIRow: FC = () => {
    const { data: stats } = useUsersStatsQuery()
    const { t } = useTranslation()

    const expiring = stats.on_hold  // proxy: on_hold ≈ expiring-soon bucket
    const overQuota = stats.limited

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: 16,
                marginBottom: 24,
            }}
        >
            <KPI
                label={t('total')}
                value={stats.total}
                accent="teal"
            />
            <KPI
                label={t('active')}
                value={stats.active}
                accent="emerald"
            />
            <KPI
                label={t('page.users.expiring_week')}
                value={expiring}
                accent="gold"
            />
            <KPI
                label={t('page.users.over_quota')}
                value={overQuota}
                accent="coral"
            />
        </div>
    )
}

export const UsersPage: FC = () => {
    const { t } = useTranslation()
    const navigate = useNavigate({ from: '/users' })

    return (
        <>
            <PanelHead
                title={t('users')}
                actions={
                    <button
                        onClick={() => navigate({ to: '/users/create' })}
                        style={{
                            background: 'hsl(var(--primary))',
                            color: 'hsl(var(--primary-foreground))',
                            border: 'none',
                            borderRadius: 8,
                            padding: '8px 18px',
                            fontWeight: 600,
                            fontSize: '0.9rem',
                            cursor: 'pointer',
                            letterSpacing: '0.01em',
                        }}
                    >
                        {t('page.users.add_user')}
                    </button>
                }
            />

            <UsersKPIRow />

            <NilouCard pad={0}>
                <UsersTable />
            </NilouCard>

            <UsersNoServiceAlert />

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </>
    )
}

export const Route = createLazyFileRoute('/_dashboard/users')({
    component: () => <UsersPage />,
})
