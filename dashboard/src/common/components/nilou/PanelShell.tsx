/**
 * PanelShell — Nilou-styled operator dashboard layout (sidebar + topbar + main).
 *
 * Replaces the upstream Marzneshin DashboardLayout (`_dashboard.tsx`)'s
 * Header + ResizablePanelGroup + DashboardSidebar combo. Single source
 * of layout for all `routes/_dashboard/*` pages.
 *
 * Design fidelity: 1:1 port of `docs/design-system-source/project/site/lib/PanelShell.jsx`,
 * with TanStack Router's <Link> in place of the design's hash-router
 * Link, and operator-scope nav (sidebarItems from features/sidebar) in
 * place of customer-scope.
 */
import type { FC, ReactNode } from 'react';
import { Suspense, useState } from 'react';
import { Link, Outlet, useRouterState } from '@tanstack/react-router';
import { Loading, Toaster } from '@marzneshin/common/components';
import { useAuth, Logout } from '@marzneshin/modules/auth';
import { sidebarItems, sidebarItemsNonSudoAdmin } from '@marzneshin/features/sidebar/items';
import type { SidebarObject } from '@marzneshin/common/components';
import { LotusMark } from './LotusMark';
import { NilouIcon } from './NilouIcon';

const navIconBtn = {
    background: 'transparent',
    border: 0,
    color: 'hsl(var(--muted-foreground))',
    cursor: 'pointer',
    padding: 6,
    display: 'grid',
    placeItems: 'center',
    borderRadius: 6,
} as const;

interface PanelShellProps {
    children?: ReactNode;
}

export const PanelShell: FC<PanelShellProps> = ({ children }) => {
    const { isSudo } = useAuth();
    const items: SidebarObject = isSudo() ? sidebarItems : sidebarItemsNonSudoAdmin;
    // P2 follow-up: fetch /admins/current for real name. For now placeholder
    // matches the existing Marzneshin behavior (it never showed admin name
    // in the topbar) — operator knows who they are.
    const adminName = isSudo() ? 'Sudo Admin' : 'Admin';
    const adminInitials = adminName.slice(0, 2).toUpperCase();

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: '256px 1fr',
                minHeight: '100vh',
                background: 'hsl(var(--muted) / 0.4)',
            }}
        >
            <aside
                style={{
                    background: 'hsl(var(--card))',
                    borderRight: '1px solid hsl(var(--border) / 0.6)',
                    padding: '20px 14px',
                    position: 'sticky',
                    top: 0,
                    height: '100vh',
                    overflowY: 'auto',
                }}
            >
                <Link
                    to="/"
                    style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '6px 10px 22px',
                        color: 'hsl(var(--foreground))',
                        fontWeight: 700,
                        fontSize: '1.02rem',
                        textDecoration: 'none',
                    }}
                >
                    <LotusMark size={26} />
                    <span>Nilou Network</span>
                </Link>
                {Object.entries(items).map(([groupTitle, groupItems]) => (
                    <NavGroup key={groupTitle} title={groupTitle} items={groupItems} />
                ))}
            </aside>

            <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                <PanelTopbar adminName={adminName} adminInitials={adminInitials} />
                <main
                    style={{
                        flex: 1,
                        padding: '28px 36px 56px',
                        overflowY: 'auto',
                    }}
                >
                    <Suspense fallback={<Loading />}>
                        {children ?? <Outlet />}
                    </Suspense>
                </main>
            </div>
            <Toaster position="top-center" />
        </div>
    );
};

interface NavGroupProps {
    title: string;
    items: SidebarObject[string];
}

const NavGroup: FC<NavGroupProps> = ({ title, items }) => {
    const { location } = useRouterState();
    const currentPath = location.pathname;

    return (
        <div style={{ marginBottom: 18 }}>
            <div
                style={{
                    padding: '8px 12px',
                    fontSize: '0.7rem',
                    letterSpacing: '0.16em',
                    textTransform: 'uppercase',
                    color: 'hsl(var(--muted-foreground))',
                    fontWeight: 600,
                }}
            >
                {title}
            </div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {items.map((it) => {
                    const isActive = currentPath === it.to || (it.to !== '/' && currentPath.startsWith(it.to));
                    return (
                        <Link
                            key={it.title}
                            to={it.to}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 10,
                                padding: '9px 12px',
                                paddingLeft: 9,
                                borderRadius: 6,
                                color: isActive ? 'hsl(var(--primary))' : 'hsl(var(--muted-foreground))',
                                background: isActive ? 'hsl(var(--primary) / 0.08)' : 'transparent',
                                fontWeight: isActive ? 600 : 500,
                                fontSize: '0.92rem',
                                borderLeft: `3px solid ${isActive ? 'hsl(var(--primary))' : 'transparent'}`,
                                textDecoration: 'none',
                            }}
                        >
                            <span style={{ display: 'inline-grid', placeItems: 'center', width: 18, height: 18 }}>{it.icon}</span>
                            <span>{it.title}</span>
                        </Link>
                    );
                })}
            </nav>
        </div>
    );
};

interface PanelTopbarProps {
    adminName: string;
    adminInitials: string;
}

const PanelTopbar: FC<PanelTopbarProps> = ({ adminName, adminInitials }) => {
    const [open, setOpen] = useState(false);
    return (
        <header
            style={{
                background: 'hsl(var(--card))',
                borderBottom: '1px solid hsl(var(--border) / 0.6)',
                padding: '14px 36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 16,
                position: 'sticky',
                top: 0,
                zIndex: 10,
            }}
        >
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    color: 'hsl(var(--muted-foreground))',
                    flex: 1,
                    maxWidth: 460,
                    padding: '8px 12px',
                    background: 'hsl(var(--muted))',
                    borderRadius: 8,
                    border: '1px solid hsl(var(--border) / 0.6)',
                }}
            >
                <NilouIcon name="search" size={16} />
                <input
                    placeholder="Search users, nodes, invoices…"
                    style={{
                        flex: 1,
                        border: 0,
                        background: 'transparent',
                        outline: 'none',
                        color: 'hsl(var(--foreground))',
                        fontFamily: 'inherit',
                        fontSize: '0.92rem',
                    }}
                />
                <kbd
                    style={{
                        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                        fontSize: '0.74rem',
                        color: 'hsl(var(--muted-foreground))',
                        background: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border) / 0.6)',
                        borderRadius: 4,
                        padding: '2px 6px',
                    }}
                >
                    ⌘K
                </kbd>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, position: 'relative' }}>
                <button type="button" style={navIconBtn} aria-label="Notifications">
                    <NilouIcon name="bell" size={18} />
                </button>
                <button type="button" style={navIconBtn} aria-label="Language">
                    <NilouIcon name="globe" size={18} />
                </button>
                <div style={{ height: 24, width: 1, background: 'hsl(var(--border) / 0.6)' }} />
                <button
                    type="button"
                    onClick={() => setOpen(!open)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        background: 'transparent',
                        border: 0,
                        cursor: 'pointer',
                        padding: 4,
                    }}
                    aria-haspopup="menu"
                    aria-expanded={open}
                >
                    <span
                        style={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary) / 0.7) 100%)',
                            color: '#fff',
                            display: 'grid',
                            placeItems: 'center',
                            fontWeight: 700,
                            fontSize: '0.86rem',
                        }}
                    >
                        {adminInitials}
                    </span>
                    <span style={{ textAlign: 'left' }}>
                        <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'hsl(var(--foreground))' }}>{adminName}</div>
                        <div style={{ fontSize: '0.74rem', color: 'hsl(var(--muted-foreground))' }}>Operator</div>
                    </span>
                    <NilouIcon name="chevronDown" size={14} />
                </button>
                {open && (
                    <div
                        role="menu"
                        style={{
                            position: 'absolute',
                            top: 'calc(100% + 8px)',
                            right: 0,
                            background: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border) / 0.6)',
                            borderRadius: 8,
                            padding: 6,
                            minWidth: 160,
                            boxShadow: '0 10px 25px rgba(20,41,64,0.08)',
                            zIndex: 20,
                        }}
                    >
                        <div style={{ padding: 8 }}>
                            <Logout />
                        </div>
                    </div>
                )}
            </div>
        </header>
    );
};
