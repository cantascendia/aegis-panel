import { type FC } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute } from "@tanstack/react-router";

import {
    Loading,
    Page,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@marzneshin/common/components";
import {
    InvoiceStatusBadge,
    useMyInvoices,
} from "@marzneshin/modules/billing/user";

/*
 * User's invoice history.
 *
 * Read-only list view: state badge, provider, total, date.
 * No row actions — re-payment of an expired invoice means
 * starting a fresh cart checkout; no "retry" magic.
 *
 * Backend endpoint `/api/billing/invoices/me` lands in A.3.1.
 * Mock gate returns `FIXTURE_MY_INVOICES` in the meantime.
 */

const formatPriceCny = (fen: number) => `¥${(fen / 100).toFixed(2)}`;
const formatTs = (iso: string) => new Date(iso).toLocaleString();

const BillingMyInvoicesPage: FC = () => {
    const { t } = useTranslation();
    const { data: rows, isLoading, isError, error } = useMyInvoices();

    if (isLoading) return <Loading />;
    if (isError) {
        return (
            <Page title={t("page.billing.my_invoices.title")}>
                <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                    {t("page.billing.my_invoices.load_error")}:{" "}
                    {(error as Error).message}
                </div>
            </Page>
        );
    }
    if (!rows || rows.length === 0) {
        return (
            <Page title={t("page.billing.my_invoices.title")}>
                <div className="text-sm text-muted-foreground text-center py-10 border rounded-md">
                    {t("page.billing.my_invoices.empty")}
                </div>
            </Page>
        );
    }

    return (
        <Page
            title={t("page.billing.my_invoices.title")}
            className="sm:w-screen md:w-full"
        >
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-16">
                            {t("page.billing.my_invoices.col.id")}
                        </TableHead>
                        <TableHead>
                            {t("page.billing.my_invoices.col.state")}
                        </TableHead>
                        <TableHead>
                            {t("page.billing.my_invoices.col.provider")}
                        </TableHead>
                        <TableHead className="text-right">
                            {t("page.billing.my_invoices.col.total")}
                        </TableHead>
                        <TableHead>
                            {t("page.billing.my_invoices.col.created_at")}
                        </TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {rows.map((inv) => (
                        <TableRow key={inv.id}>
                            <TableCell className="font-mono text-xs">
                                #{inv.id}
                            </TableCell>
                            <TableCell>
                                <InvoiceStatusBadge state={inv.state} />
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                                {inv.provider}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                                {formatPriceCny(inv.total_cny_fen)}
                            </TableCell>
                            <TableCell className="text-xs">
                                {formatTs(inv.created_at)}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/my-invoices")({
    component: BillingMyInvoicesPage,
});
