/**
 * Dashboard layout — Nilou Network operator panel.
 *
 * Replaces the upstream Marzneshin layout (Header + ResizablePanelGroup +
 * DashboardSidebar) with the Nilou-styled `PanelShell`. Same auth gate
 * (`beforeLoad` redirects to /login if not authenticated). Outlet renders
 * inside PanelShell's main area with Suspense + Loading fallback.
 *
 * The legacy DashboardLayout / DashboardSidebar / Header / CommandBox /
 * GithubRepo components are still present in the codebase for any place
 * that wants them, but no longer mount on /_dashboard.
 *
 * AEGIS fork — wave-S of dashboard rewrite. Was upstream sync zone, now
 * fork-owned. See docs/ai-cto/SPEC-dashboard-rewrite.md.
 */
import { createFileRoute, redirect } from "@tanstack/react-router";
import { useAuth } from "@marzneshin/modules/auth";
import { PanelShell } from "@marzneshin/common/components/nilou";

export const Route = createFileRoute("/_dashboard")({
    component: PanelShell,
    beforeLoad: async () => {
        const loggedIn = await useAuth.getState().isLoggedIn();
        if (!loggedIn) {
            throw redirect({ to: "/login" });
        }
    },
});
