import { Loading } from '@marzneshin/common/components'
import { SudoRoute } from '@marzneshin/libs/sudo-routes'
import { createLazyFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import {
    AdminsTable,
    useAdminsQuery,
} from '@marzneshin/modules/admins'
import {
    KPI,
    PanelHead,
    NilouCard,
} from '@marzneshin/common/components/nilou'
import { type FC, Suspense } from 'react'
import { useTranslation } from 'react-i18next'

/** KPI row for /admins operator view */
const AdminsKPIRow: FC = () => {
    const { data } = useAdminsQuery({ page: 1, size: 1000, filters: {} })
    const { t } = useTranslation()

    const admins = data.entities
    const total = data.pageCount > 0 ? admins.length : admins.length
    const sudo = admins.filter((a) => a.is_sudo).length
    const enabled = admins.filter((a) => a.enabled).length

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
                label={t('page.admins.total')}
                value={total}
                accent="teal"
            />
            <KPI
                label={t('page.admins.sudo')}
                value={sudo}
                accent="gold"
            />
            <KPI
                label={t('page.admins.enabled')}
                value={enabled}
                accent="emerald"
            />
        </div>
    )
}

export const AdminsPage: FC = () => {
    const { t } = useTranslation()
    const navigate = useNavigate({ from: '/admins' })

    return (
        <>
            <PanelHead
                title={t('admins')}
                actions={
                    <button
                        onClick={() => navigate({ to: '/admins/create' })}
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
                        {t('page.admins.create_admin')}
                    </button>
                }
            />

            <AdminsKPIRow />

            <NilouCard pad={0}>
                <AdminsTable />
            </NilouCard>

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </>
    )
}

export const Route = createLazyFileRoute('/_dashboard/admins')({
    component: () => (
        <SudoRoute>
            <AdminsPage />
        </SudoRoute>
    ),
})
