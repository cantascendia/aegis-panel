import { type FC, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
    Button,
} from "@marzneshin/common/components";

import { useInvoicePoll } from "../api/invoice-poll.query";
import type { Invoice } from "../../types";
import { INVOICE_TERMINAL_STATES } from "../../types";
import { InvoiceStatusBadge } from "./invoice-status-badge";

/*
 * TRC20 payment screen.
 *
 * Shown after user picks TRC20 at checkout. Displays:
 * - State badge (awaiting_payment → paid → applied)
 * - Expected USDT amount (from invoice.trc20_expected_amount_millis)
 * - Memo (unique per-invoice for on-chain correlation; operator's
 *   wallet-software users should prepend this to the tx memo)
 * - Countdown to `expires_at` (30-min payment window by default)
 * - "Copy memo" and "Copy amount" buttons for wallet paste
 *
 * Polls `GET /api/billing/invoices/{id}` every 5 s via
 * `useInvoicePoll`; stops when state hits a terminal.
 *
 * NO QR code image yet — that's a qrcode lib decision (qr.js?
 * next-qrcode? SVG) deferred to the flip-on PR. For the skeleton,
 * showing the memo + amount text plainly is enough to validate the
 * flow.
 */

const formatUsdtMillis = (millis: number | null): string => {
    if (millis === null) return "—";
    return `${(millis / 1000).toFixed(3)} USDT`;
};

const formatMinSec = (totalSeconds: number): string => {
    if (totalSeconds <= 0) return "00:00";
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};

interface CountdownProps {
    expiresAt: string;
}

const Countdown: FC<CountdownProps> = ({ expiresAt }) => {
    const { t } = useTranslation();
    const target = new Date(expiresAt).getTime();
    const [remainingSec, setRemainingSec] = useState(() =>
        Math.max(0, Math.floor((target - Date.now()) / 1000)),
    );

    useEffect(() => {
        const id = setInterval(() => {
            setRemainingSec(Math.max(0, Math.floor((target - Date.now()) / 1000)));
        }, 1_000);
        return () => clearInterval(id);
    }, [target]);

    return (
        <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">
                {t("page.billing.purchase.trc20.countdown")}
            </span>
            <span className="text-2xl font-mono tabular-nums">
                {formatMinSec(remainingSec)}
            </span>
        </div>
    );
};

interface CopyFieldProps {
    label: string;
    value: string;
    mono?: boolean;
}

const CopyField: FC<CopyFieldProps> = ({ label, value, mono = false }) => {
    const { t } = useTranslation();
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
        if (!navigator.clipboard) return;
        await navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1_500);
    };
    return (
        <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">{label}</span>
            <div className="flex flex-row gap-2 items-center">
                <code
                    className={
                        mono
                            ? "flex-1 px-2 py-1 border rounded-md text-sm font-mono"
                            : "flex-1 px-2 py-1 border rounded-md text-sm"
                    }
                >
                    {value}
                </code>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopy}
                    disabled={!navigator.clipboard}
                >
                    {copied
                        ? t("page.billing.purchase.trc20.copied")
                        : t("page.billing.purchase.trc20.copy")}
                </Button>
            </div>
        </div>
    );
};

interface Trc20PaymentScreenProps {
    invoiceId: number;
    /** When used after checkout, the first render can seed with the
     *  CheckoutResponse's companion invoice so we don't flash a
     *  loading state. Optional. */
    seed?: Invoice;
}

export const Trc20PaymentScreen: FC<Trc20PaymentScreenProps> = ({
    invoiceId,
    seed,
}) => {
    const { t } = useTranslation();
    const { data: polled, isLoading, isError, error } = useInvoicePoll(invoiceId);
    const invoice = polled ?? seed;

    if (isLoading && !seed) {
        return (
            <div className="text-sm text-muted-foreground p-6 text-center">
                {t("page.billing.purchase.trc20.loading")}
            </div>
        );
    }
    if (isError || !invoice) {
        return (
            <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                {t("page.billing.purchase.trc20.load_error")}:{" "}
                {(error as Error | null)?.message ?? "unknown"}
            </div>
        );
    }

    const isTerminal = INVOICE_TERMINAL_STATES.includes(invoice.state);

    return (
        <div className="flex flex-col gap-4 max-w-md">
            <div className="flex flex-row justify-between items-start">
                <div className="flex flex-col gap-1">
                    <h2 className="text-xl font-semibold">
                        {t("page.billing.purchase.trc20.title")} #{invoice.id}
                    </h2>
                    <InvoiceStatusBadge state={invoice.state} />
                </div>
                {!isTerminal && <Countdown expiresAt={invoice.expires_at} />}
            </div>

            {!isTerminal && (
                <>
                    <CopyField
                        label={t("page.billing.purchase.trc20.amount_label")}
                        value={formatUsdtMillis(
                            invoice.trc20_expected_amount_millis,
                        )}
                        mono
                    />
                    <CopyField
                        label={t("page.billing.purchase.trc20.memo_label")}
                        value={invoice.trc20_memo ?? "—"}
                        mono
                    />
                    <p className="text-xs text-muted-foreground">
                        {t("page.billing.purchase.trc20.instructions")}
                    </p>
                </>
            )}

            {invoice.state === "paid" && (
                <div className="text-sm p-3 rounded-md bg-muted">
                    {t("page.billing.purchase.trc20.paid_waiting_apply")}
                </div>
            )}
            {invoice.state === "applied" && (
                <div className="text-sm p-3 rounded-md bg-primary/10 text-primary">
                    {t("page.billing.purchase.trc20.applied")}
                </div>
            )}
            {(invoice.state === "expired" ||
                invoice.state === "cancelled" ||
                invoice.state === "failed") && (
                <div className="text-sm p-3 rounded-md bg-destructive/10 text-destructive">
                    {t("page.billing.purchase.trc20.terminal_failure")}
                </div>
            )}
        </div>
    );
};
