import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";

import {
    Badge,
    Button,
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    Loading,
    ScrollArea,
    Textarea,
} from "@marzneshin/common/components";

import {
    useAdminInvoice,
    useApplyManual,
    useCancelInvoice,
    useInvoiceEvents,
} from "../api";
import type { Invoice, InvoiceState } from "../types";
import { INVOICE_TERMINAL_STATES } from "../types";

/*
 * InvoiceDetailDialog — admin view of one invoice.
 *
 * Two "mode" panels share this dialog:
 *   - Read-only header: invoice summary + lines + audit events
 *   - Action footer: apply_manual + cancel buttons (hidden on
 *     terminal states, since the backend rejects with 409)
 *
 * Actions require a note (backend enforces) — we gate the button
 * on non-empty textarea and pass the note verbatim.
 *
 * State badge color maps semantically:
 *   - applied → default (green-ish in most themes)
 *   - paid / awaiting_payment → secondary
 *   - expired / cancelled / failed → destructive
 *   - created / pending → outline
 */

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

interface InvoiceDetailDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    invoiceId: number | null;
}

export const InvoiceDetailDialog: FC<InvoiceDetailDialogProps> = ({
    open,
    onOpenChange,
    invoiceId,
}) => {
    const { t } = useTranslation();
    const {
        data: invoice,
        isLoading,
        isError,
        error,
    } = useAdminInvoice(invoiceId, { enabled: open });
    const { data: events } = useInvoiceEvents(invoiceId, {
        enabled: open,
    });

    const applyMutation = useApplyManual();
    const cancelMutation = useCancelInvoice();

    const [note, setNote] = useState("");

    const onApply = async () => {
        if (!invoice || !note.trim()) return;
        await applyMutation.mutateAsync({
            id: invoice.id,
            body: { note: note.trim() },
        });
        setNote("");
        onOpenChange(false);
    };

    const onCancel = async () => {
        if (!invoice || !note.trim()) return;
        await cancelMutation.mutateAsync({
            id: invoice.id,
            body: { note: note.trim() },
        });
        setNote("");
        onOpenChange(false);
    };

    const isTerminal =
        invoice !== undefined &&
        INVOICE_TERMINAL_STATES.includes(invoice.state);
    const pending =
        applyMutation.isPending || cancelMutation.isPending;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>
                        {t("page.billing.invoices.detail.title")}
                        {invoice ? ` #${invoice.id}` : ""}
                    </DialogTitle>
                    <DialogDescription>
                        {t("page.billing.invoices.detail.desc")}
                    </DialogDescription>
                </DialogHeader>

                {isLoading && <Loading />}
                {isError && (
                    <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                        {t("page.billing.invoices.detail.load_error")}:{" "}
                        {(error as Error).message}
                    </div>
                )}

                {invoice && (
                    <DetailBody
                        invoice={invoice}
                        events={events ?? []}
                        note={note}
                        onNoteChange={setNote}
                    />
                )}

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        {t("close")}
                    </Button>
                    {invoice && !isTerminal && (
                        <>
                            <Button
                                variant="secondary"
                                onClick={onCancel}
                                disabled={pending || !note.trim()}
                            >
                                {pending && cancelMutation.isPending
                                    ? t("page.billing.invoices.action.cancelling")
                                    : t("page.billing.invoices.action.cancel")}
                            </Button>
                            <Button
                                onClick={onApply}
                                disabled={pending || !note.trim()}
                            >
                                {pending && applyMutation.isPending
                                    ? t("page.billing.invoices.action.applying")
                                    : t("page.billing.invoices.action.apply_manual")}
                            </Button>
                        </>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};


interface DetailBodyProps {
    invoice: Invoice;
    events: { id: number; event_type: string; note: string | null; created_at: string; payload_json: Record<string, unknown> }[];
    note: string;
    onNoteChange: (s: string) => void;
}

const DetailBody: FC<DetailBodyProps> = ({
    invoice,
    events,
    note,
    onNoteChange,
}) => {
    const { t } = useTranslation();
    const isTerminal = INVOICE_TERMINAL_STATES.includes(invoice.state);
    // Extract to a const so the extractor regex sees a single-line t("...") call;
    // biome wraps long t() calls inside JSX attributes across lines, which hides
    // the key from the line-based scanner in scripts/check_translations.sh.
    const notePlaceholder = t("page.billing.invoices.action.note_placeholder");

    return (
        <div className="flex flex-col gap-4">
            {/* Header grid */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <div>
                    <span className="text-muted-foreground">
                        {t("page.billing.invoices.detail.user_id")}:
                    </span>{" "}
                    {invoice.user_id}
                </div>
                <div>
                    <span className="text-muted-foreground">
                        {t("page.billing.invoices.detail.state")}:
                    </span>{" "}
                    <Badge variant={stateBadgeVariant(invoice.state)}>
                        {invoice.state}
                    </Badge>
                </div>
                <div>
                    <span className="text-muted-foreground">
                        {t("page.billing.invoices.detail.provider")}:
                    </span>{" "}
                    <span className="font-mono text-xs">{invoice.provider}</span>
                </div>
                <div>
                    <span className="text-muted-foreground">
                        {t("page.billing.invoices.detail.total")}:
                    </span>{" "}
                    <span className="tabular-nums font-semibold">
                        {formatPriceCny(invoice.total_cny_fen)}
                    </span>
                </div>
                <div>
                    <span className="text-muted-foreground">
                        {t("page.billing.invoices.detail.created_at")}:
                    </span>{" "}
                    {formatTs(invoice.created_at)}
                </div>
                <div>
                    <span className="text-muted-foreground">
                        {t("page.billing.invoices.detail.expires_at")}:
                    </span>{" "}
                    {formatTs(invoice.expires_at)}
                </div>
                {invoice.paid_at && (
                    <div>
                        <span className="text-muted-foreground">
                            {t("page.billing.invoices.detail.paid_at")}:
                        </span>{" "}
                        {formatTs(invoice.paid_at)}
                    </div>
                )}
                {invoice.applied_at && (
                    <div>
                        <span className="text-muted-foreground">
                            {t("page.billing.invoices.detail.applied_at")}:
                        </span>{" "}
                        {formatTs(invoice.applied_at)}
                    </div>
                )}
            </div>

            {/* TRC20 correlation */}
            {(invoice.trc20_memo ||
                invoice.trc20_expected_amount_millis !== null) && (
                <div className="text-xs text-muted-foreground bg-muted/40 p-2 rounded-md">
                    <div>
                        {t("page.billing.invoices.detail.trc20_memo")}:{" "}
                        <span className="font-mono">
                            {invoice.trc20_memo ?? "—"}
                        </span>
                    </div>
                    {invoice.trc20_expected_amount_millis !== null && (
                        <div>
                            {t("page.billing.invoices.detail.trc20_amount")}:{" "}
                            <span className="font-mono tabular-nums">
                                {(
                                    invoice.trc20_expected_amount_millis /
                                    1000
                                ).toFixed(3)}{" "}
                                USDT
                            </span>
                        </div>
                    )}
                </div>
            )}

            {/* Lines */}
            <section>
                <h3 className="text-sm font-semibold mb-1">
                    {t("page.billing.invoices.detail.lines_title")}
                </h3>
                {invoice.lines.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                        {t("page.billing.invoices.detail.lines_empty")}
                    </p>
                ) : (
                    <div className="flex flex-col gap-1">
                        {invoice.lines.map((ln) => (
                            <div
                                key={ln.id}
                                className="flex flex-row justify-between text-xs border-b last:border-b-0 py-1"
                            >
                                <span className="font-mono">
                                    plan #{ln.plan_id}
                                </span>
                                <span className="text-muted-foreground">
                                    × {ln.quantity}
                                </span>
                                <span className="tabular-nums">
                                    {formatPriceCny(
                                        ln.unit_price_fen_at_purchase *
                                            ln.quantity,
                                    )}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Events / audit log */}
            <section>
                <h3 className="text-sm font-semibold mb-1">
                    {t("page.billing.invoices.detail.events_title")}
                </h3>
                {events.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                        {t("page.billing.invoices.detail.events_empty")}
                    </p>
                ) : (
                    <ScrollArea className="h-32 border rounded-md">
                        <div className="flex flex-col gap-1 p-2 text-xs">
                            {events.map((ev) => (
                                <div
                                    key={ev.id}
                                    className="border-b last:border-b-0 py-1"
                                >
                                    <div className="flex flex-row justify-between">
                                        <span className="font-mono">
                                            {ev.event_type}
                                        </span>
                                        <span className="text-muted-foreground">
                                            {formatTs(ev.created_at)}
                                        </span>
                                    </div>
                                    {ev.note && (
                                        <div className="text-muted-foreground italic">
                                            {ev.note}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                )}
            </section>

            {/* Action panel — only for non-terminal invoices */}
            {!isTerminal && (
                <section className="flex flex-col gap-1">
                    <label
                        htmlFor="invoice-note"
                        className="text-sm font-semibold"
                    >
                        {t("page.billing.invoices.action.note_label")}
                    </label>
                    <Textarea
                        id="invoice-note"
                        value={note}
                        onChange={(e) => onNoteChange(e.target.value)}
                        placeholder={notePlaceholder}
                        rows={2}
                    />
                    <p className="text-xs text-muted-foreground">
                        {t("page.billing.invoices.action.note_hint")}
                    </p>
                </section>
            )}
        </div>
    );
};
