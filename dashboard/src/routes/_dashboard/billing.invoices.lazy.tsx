/**
 * /billing/invoices — System-wide invoice list. Wave-B2 Nilou rewrite.
 *
 * Layout:
 *   PanelHead → 3-KPI row (MRR / Unpaid / Paid total) → NilouCard(InvoicesTable)
 *
 * KPI values are derived client-side from the invoices already fetched
 * by InvoicesTable (we fetch with limit=100 for the table; KPIs reflect
 * that window — good enough for ops dashboards). No extra network call.
 *
 * Forbidden-path note: billing UI per .claude/rules/forbidden-paths.md.
 * PR must carry the `requires-double-review` label.
 */

import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading } from "@marzneshin/common/components";
import {
    KPI,
    NilouCard,
    PanelHead,
} from "@marzneshin/common/components/nilou";
import { InvoicesTable } from "@marzneshin/modules/billing";
import { useAdminInvoices } from "@marzneshin/modules/billing/api";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fenToYuan = (fen: number): string => `¥${(fen / 100).toFixed(0)}`;

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

// ---------------------------------------------------------------------------
// KPI row — derived from a separate all-invoices fetch (no state filter)
// ---------------------------------------------------------------------------

const InvoicesKPIRow: FC = () => {
    const { t } = useTranslation();
    const { data: allInvoices } = useAdminInvoices({ limit: 500 });

    const invoices = allInvoices ?? [];
    const now = Date.now();
    const cutoff = now - THIRTY_DAYS_MS;

    // MRR proxy: sum of "applied" / "paid" invoices in last 30 days
    const mrr = invoices
        .filter((inv) => {
            const isPaid = inv.state === "applied" || inv.state === "paid";
            if (!isPaid) return false;
            const ts = new Date(inv.created_at).getTime();
            return ts >= cutoff;
        })
        .reduce((sum, inv) => sum + inv.total_cny_fen, 0);

    // Unpaid: pending or awaiting_payment
    const unpaidCount = invoices.filter(
        (inv) =>
            inv.state === "pending" || inv.state === "awaiting_payment" || inv.state === "created",
    ).length;

    // Paid total all-time (applied = successfully applied to user)
    const paidTotal = invoices
        .filter((inv) => inv.state === "applied" || inv.state === "paid")
        .reduce((sum, inv) => sum + inv.total_cny_fen, 0);

    return (
        <div
            style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                gap: 16,
                marginBottom: 24,
            }}
        >
            <KPI
                label={t("nilou.billing.kpi.mrr", "MRR (30d)")}
                value={fenToYuan(mrr)}
                accent="emerald"
            />
            <KPI
                label={t("nilou.billing.kpi.unpaid", "Unpaid")}
                value={unpaidCount}
                accent={unpaidCount > 0 ? "gold" : "teal"}
            />
            <KPI
                label={t("nilou.billing.kpi.paid_total", "Paid total")}
                value={fenToYuan(paidTotal)}
                accent="teal"
            />
        </div>
    );
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export const BillingInvoicesPage: FC = () => {
    const { t } = useTranslation();

    return (
        <>
            <PanelHead
                title={t("page.billing.invoices.title")}
                sub={t("page.billing.invoices.subtitle")}
            />

            <InvoicesKPIRow />

            <NilouCard pad={0}>
                <InvoicesTable />
            </NilouCard>

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/invoices")({
    component: () => (
        <SudoRoute>
            <BillingInvoicesPage />
        </SudoRoute>
    ),
});
