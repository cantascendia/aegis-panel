import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { Eye } from "lucide-react";

import {
    Badge,
    Button,
    Input,
    Label,
    Loading,
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@marzneshin/common/components";

import { useAdminInvoices } from "../api";
import type { Invoice, InvoiceState } from "../types";
import { InvoiceDetailDialog } from "./invoice-detail-dialog";

const formatPriceCny = (fen: number) => `¥${(fen / 100).toFixed(2)}`;
const formatTs = (iso: string) => new Date(iso).toLocaleString();

const stateBadgeVariant = (
    state: InvoiceState,
): "default" | "secondary" | "outline" | "destructive" => {
    if (state === "applied") return "default";
    if (state === "paid" || state === "awaiting_payment") return "secondary";
    if (
        state === "expired" ||
        state === "cancelled" ||
        state === "failed"
    ) {
        return "destructive";
    }
    return "outline";
};

// i18next doesn't accept template-literal keys (the extractor can't
// see them), so map state enum to a literal t() call inline.
const StateLabel: FC<{ state: InvoiceState }> = ({ state }) => {
    const { t } = useTranslation();
    // Use the raw state string as the display — admins know these —
    // instead of adding 8 locale keys we don't need. Admin UI is
    // intentionally terse; user-facing A.4 flow will have friendlier
    // labels.
    void t; // silence unused-var lint while keeping import consistent
    return <Badge variant={stateBadgeVariant(state)}>{state}</Badge>;
};

const STATE_FILTER_VALUES: ("" | InvoiceState)[] = [
    "",
    "created",
    "pending",
    "awaiting_payment",
    "paid",
    "applied",
    "expired",
    "cancelled",
    "failed",
];

export const InvoicesTable: FC = () => {
    const { t } = useTranslation();

    const [stateFilter, setStateFilter] = useState<"" | InvoiceState>("");
    const [userIdInput, setUserIdInput] = useState<string>("");
    const [detailOpen, setDetailOpen] = useState(false);
    const [selectedId, setSelectedId] = useState<number | null>(null);

    const userIdFilter =
        userIdInput.trim() === ""
            ? undefined
            : Number.parseInt(userIdInput, 10);
    const validUserId =
        userIdFilter !== undefined && Number.isFinite(userIdFilter)
            ? userIdFilter
            : undefined;

    const {
        data: invoices,
        isLoading,
        isError,
        error,
    } = useAdminInvoices({
        state: stateFilter === "" ? undefined : stateFilter,
        user_id: validUserId,
        limit: 100,
    });

    const openDetail = (invoice: Invoice) => {
        setSelectedId(invoice.id);
        setDetailOpen(true);
    };

    return (
        <div className="flex flex-col gap-3">
            <div>
                <h2 className="text-lg font-semibold">
                    {t("page.billing.invoices.title")}
                </h2>
                <p className="text-sm text-muted-foreground">
                    {t("page.billing.invoices.subtitle")}
                </p>
            </div>

            {/* Filters */}
            <div className="flex flex-row gap-2 items-end">
                <div className="flex flex-col gap-1 w-40">
                    <Label htmlFor="inv-state">
                        {t("page.billing.invoices.filter.state")}
                    </Label>
                    <Select
                        value={stateFilter === "" ? "__any" : stateFilter}
                        onValueChange={(v) =>
                            setStateFilter(v === "__any" ? "" : (v as InvoiceState))
                        }
                    >
                        <SelectTrigger id="inv-state">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="__any">
                                {t("page.billing.invoices.filter.state_any")}
                            </SelectItem>
                            {STATE_FILTER_VALUES.filter((s) => s !== "").map(
                                (s) => (
                                    <SelectItem key={s} value={s}>
                                        {s}
                                    </SelectItem>
                                ),
                            )}
                        </SelectContent>
                    </Select>
                </div>
                <div className="flex flex-col gap-1 w-32">
                    <Label htmlFor="inv-user">
                        {t("page.billing.invoices.filter.user_id")}
                    </Label>
                    <Input
                        id="inv-user"
                        type="number"
                        min={1}
                        value={userIdInput}
                        onChange={(e) => setUserIdInput(e.target.value)}
                        placeholder="1"
                    />
                </div>
            </div>

            {isLoading && <Loading />}
            {isError && (
                <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                    {t("page.billing.invoices.load_error")}:{" "}
                    {(error as Error).message}
                </div>
            )}

            {invoices && invoices.length === 0 && (
                <div className="text-sm text-muted-foreground text-center py-10 border rounded-md">
                    {t("page.billing.invoices.empty")}
                </div>
            )}

            {invoices && invoices.length > 0 && (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-16">
                                {t("page.billing.invoices.col.id")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.invoices.col.user_id")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.invoices.col.state")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.invoices.col.provider")}
                            </TableHead>
                            <TableHead className="text-right">
                                {t("page.billing.invoices.col.total")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.invoices.col.created_at")}
                            </TableHead>
                            <TableHead className="w-10" />
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {invoices.map((inv) => (
                            <TableRow key={inv.id}>
                                <TableCell className="font-mono text-xs">
                                    #{inv.id}
                                </TableCell>
                                <TableCell>{inv.user_id}</TableCell>
                                <TableCell>
                                    <StateLabel state={inv.state} />
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
                                <TableCell>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => openDetail(inv)}
                                    >
                                        <Eye className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            )}

            <InvoiceDetailDialog
                open={detailOpen}
                onOpenChange={setDetailOpen}
                invoiceId={selectedId}
            />
        </div>
    );
};
