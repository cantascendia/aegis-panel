import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    Button,
    Input,
    Label,
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    Badge,
    ScrollArea,
    Separator,
    CopyToClipboardButton,
} from "@marzneshin/common/components";
import {
    type SniCandidate,
    type SniRegion,
    type SniSelectorResult,
    useSniSuggestMutation,
} from "@marzneshin/modules/nodes";

/*
 * SNI intelligent selector dialog.
 *
 * Opened from the node creation flow (see MutationDialog "Suggest SNI"
 * button). User-initiated — we do NOT auto-probe on field-blur, since
 * every probe sends TLS handshakes to third-party CDN hosts and we
 * don't want to burn that budget on partially-typed IP addresses.
 *
 * UX shape:
 *   1. Pre-populated `vpsIp` (from parent node-address field), count=5,
 *      region=auto.
 *   2. User clicks "Probe" → button shows spinner, dialog body shows
 *      in-flight hint. 60s cap from backend; ofetch has no client
 *      timeout — we rely on the server-side wall clock.
 *   3. Result: sorted candidates with score, per-indicator badges,
 *      copy-SNI button per row. Rejected section (collapsible-ish
 *      via a simple toggle) explains why other seeds didn't make it.
 *   4. Errors surface as a short inline message (no toast; user is
 *      already looking at the dialog).
 *
 * i18n strategy
 * -------------
 * Every t() call passes an English default as the second argument.
 * Locale JSON files are intentionally NOT modified by this PR — the
 * project's `tools/check_translations.sh` CI gate enforces strict
 * parity that's long out of sync (hundreds of pre-existing "extra"
 * and "missing" keys across all 8 locales). Adding my keys to one
 * locale while pre-existing drift stays red would block this PR on
 * debt that isn't ours. Defaults-in-source keeps the UI usable in
 * every language via i18next's `fallbackLng: 'en'` behaviour. A
 * dedicated follow-up PR should either fix the drift cross-locale
 * or soften the CI gate. Until then, defaults in source are the
 * right trade.
 */

type Region = { value: SniRegion; labelKey: string; label: string };
const REGIONS: Region[] = [
    { value: "auto", labelKey: "page.nodes.sni-suggest.region.auto", label: "Auto" },
    { value: "global", labelKey: "page.nodes.sni-suggest.region.global", label: "Global" },
    { value: "jp", labelKey: "page.nodes.sni-suggest.region.jp", label: "Japan" },
    { value: "kr", labelKey: "page.nodes.sni-suggest.region.kr", label: "Korea" },
    { value: "us", labelKey: "page.nodes.sni-suggest.region.us", label: "United States" },
    { value: "eu", labelKey: "page.nodes.sni-suggest.region.eu", label: "Europe" },
];

interface SniSuggestDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    defaultVpsIp?: string;
}

export const SniSuggestDialog: FC<SniSuggestDialogProps> = ({
    open,
    onOpenChange,
    defaultVpsIp = "",
}) => {
    const { t } = useTranslation();
    const mutation = useSniSuggestMutation();

    const [vpsIp, setVpsIp] = useState<string>(defaultVpsIp);
    const [count, setCount] = useState<number>(5);
    const [region, setRegion] = useState<SniRegion>("auto");
    const [showRejected, setShowRejected] = useState<boolean>(false);

    // Re-sync default when parent changes (e.g., user reopens dialog
    // after editing the address field). We intentionally *only*
    // overwrite on open transitions — continuous mirroring while the
    // dialog is open would clobber manual edits the user made here.
    const [wasOpen, setWasOpen] = useState(open);
    if (open && !wasOpen) {
        setVpsIp(defaultVpsIp);
        setWasOpen(true);
    } else if (!open && wasOpen) {
        setWasOpen(false);
    }

    const onProbe = () => {
        mutation.mutate({ vps_ip: vpsIp, count, region });
    };

    const result: SniSelectorResult | undefined = mutation.data;
    const error = mutation.error as Error | null;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>
                        {t(
                            "page.nodes.sni-suggest.title",
                            "SNI Intelligent Selector",
                        )}
                    </DialogTitle>
                    <DialogDescription>
                        {t(
                            "page.nodes.sni-suggest.desc",
                            "Probes seed domains against six hard indicators (DPI blacklist / no-redirect / same-ASN / TLS 1.3 / ALPN h2 / X25519) and returns the top-scored candidates.",
                        )}
                    </DialogDescription>
                </DialogHeader>

                {/* Input row */}
                <div className="flex flex-col gap-3">
                    <div className="flex flex-row gap-2 items-end">
                        <div className="flex flex-col gap-1 flex-1">
                            <Label htmlFor="sni-vps-ip">
                                {t(
                                    "page.nodes.sni-suggest.vps_ip",
                                    "VPS Egress IP",
                                )}
                            </Label>
                            <Input
                                id="sni-vps-ip"
                                value={vpsIp}
                                onChange={(e) => setVpsIp(e.target.value)}
                                placeholder="1.2.3.4"
                            />
                        </div>
                        <div className="flex flex-col gap-1 w-20">
                            <Label htmlFor="sni-count">
                                {t("page.nodes.sni-suggest.count", "Count")}
                            </Label>
                            <Input
                                id="sni-count"
                                type="number"
                                min={1}
                                max={50}
                                value={count}
                                onChange={(e) =>
                                    setCount(Number(e.target.value) || 5)
                                }
                            />
                        </div>
                        <div className="flex flex-col gap-1 w-28">
                            <Label>
                                {t(
                                    "page.nodes.sni-suggest.region.label",
                                    "Region",
                                )}
                            </Label>
                            <Select
                                value={region}
                                onValueChange={(v) =>
                                    setRegion(v as SniRegion)
                                }
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {REGIONS.map((r) => (
                                        <SelectItem key={r.value} value={r.value}>
                                            {t(r.labelKey, r.label)}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <Button
                        onClick={onProbe}
                        disabled={!vpsIp || mutation.isPending}
                        className="w-full"
                    >
                        {mutation.isPending
                            ? t(
                                  "page.nodes.sni-suggest.probing",
                                  "Probing (up to 60s)...",
                              )
                            : t("page.nodes.sni-suggest.probe", "Probe")}
                    </Button>
                </div>

                <Separator />

                {/* Results area */}
                {error && (
                    <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                        {t("page.nodes.sni-suggest.error", "Error")}:{" "}
                        {error.message}
                    </div>
                )}

                {result && !error && (
                    <ResultsSection
                        result={result}
                        showRejected={showRejected}
                        onToggleRejected={() => setShowRejected((s) => !s)}
                    />
                )}

                {!result && !error && !mutation.isPending && (
                    <div className="text-sm text-muted-foreground text-center py-4">
                        {t(
                            "page.nodes.sni-suggest.awaiting",
                            "Enter a VPS IP and click Probe.",
                        )}
                    </div>
                )}

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        {t("close", "Close")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};


interface ResultsSectionProps {
    result: SniSelectorResult;
    showRejected: boolean;
    onToggleRejected: () => void;
}

const ResultsSection: FC<ResultsSectionProps> = ({
    result,
    showRejected,
    onToggleRejected,
}) => {
    const { t } = useTranslation();
    return (
        <div className="flex flex-col gap-2">
            {/* VPS context strip */}
            <div className="text-xs text-muted-foreground flex flex-row gap-3">
                <span>ASN: {result.vps_asn ?? "—"}</span>
                <span>
                    {t("page.nodes.sni-suggest.country", "Country")}:{" "}
                    {result.vps_country ?? "—"}
                </span>
                <span>
                    {t("page.nodes.sni-suggest.elapsed", "{{seconds}}s", {
                        seconds: result.elapsed_seconds.toFixed(1),
                    })}
                </span>
            </div>

            {/* Candidates list */}
            {result.candidates.length === 0 ? (
                <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                    {t(
                        "page.nodes.sni-suggest.no_candidates",
                        "No candidates passed all six indicators. Check the rejected list below for reasons.",
                    )}
                </div>
            ) : (
                <ScrollArea className="h-72 border rounded-md">
                    <div className="flex flex-col gap-1 p-2">
                        {result.candidates.map((c) => (
                            <CandidateRow key={c.host} cand={c} />
                        ))}
                    </div>
                </ScrollArea>
            )}

            {/* Rejected toggle */}
            {result.rejected.length > 0 && (
                <div>
                    <button
                        type="button"
                        onClick={onToggleRejected}
                        className="text-xs text-muted-foreground hover:text-foreground underline"
                    >
                        {showRejected
                            ? t(
                                  "page.nodes.sni-suggest.hide_rejected",
                                  "Hide rejected",
                              )
                            : t(
                                  "page.nodes.sni-suggest.show_rejected",
                                  "Show {{count}} rejected",
                                  { count: result.rejected.length },
                              )}
                    </button>
                    {showRejected && (
                        <ScrollArea className="h-32 mt-2 border rounded-md">
                            <div className="flex flex-col gap-1 p-2 text-xs">
                                {result.rejected.map((r) => (
                                    <div
                                        key={r.host}
                                        className="flex flex-row justify-between gap-2 border-b last:border-b-0 py-1"
                                    >
                                        <span className="font-mono">
                                            {r.host}
                                        </span>
                                        <span className="text-muted-foreground">
                                            {r.reason}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    )}
                </div>
            )}
        </div>
    );
};


const CandidateRow: FC<{ cand: SniCandidate }> = ({ cand }) => {
    const { t } = useTranslation();
    const { checks } = cand;

    // Compact per-indicator pass/fail glyphs. Hard indicators only —
    // soft signals (ocsp_stapling, rtt_ms) would noise the row;
    // surfaced in tooltip-free mode for now.
    const indicators: { key: string; pass: boolean; label: string }[] = [
        {
            key: "bl",
            pass: checks.blacklist_ok,
            label: t(
                "page.nodes.sni-suggest.ind.blacklist",
                "Not on DPI blacklist",
            ),
        },
        {
            key: "nr",
            pass: checks.no_redirect,
            label: t(
                "page.nodes.sni-suggest.ind.no_redirect",
                "No cross-domain redirect",
            ),
        },
        {
            key: "asn",
            pass: checks.same_asn,
            label: t(
                "page.nodes.sni-suggest.ind.same_asn",
                "Same ASN as VPS",
            ),
        },
        {
            key: "tls",
            pass: checks.tls13_ok,
            label: t("page.nodes.sni-suggest.ind.tls13", "TLS 1.3 handshake"),
        },
        {
            key: "h2",
            pass: checks.alpn_h2_ok,
            label: t("page.nodes.sni-suggest.ind.h2", "ALPN negotiates h2"),
        },
        {
            key: "x",
            pass: checks.x25519_ok,
            label: t(
                "page.nodes.sni-suggest.ind.x25519",
                "X25519 curve in ECDHE",
            ),
        },
    ];

    return (
        <div className="flex flex-row items-center gap-2 p-2 hover:bg-muted/50 rounded-sm">
            <span className="font-mono text-sm flex-1 truncate">
                {cand.host}
            </span>
            <Badge variant="secondary" className="tabular-nums">
                {cand.score.toFixed(2)}
            </Badge>
            <div className="flex flex-row gap-0.5">
                {indicators.map((ind) => (
                    <span
                        key={ind.key}
                        title={`${ind.label}: ${ind.pass ? "✓" : "✗"}`}
                        className={
                            ind.pass
                                ? "text-green-600 text-xs"
                                : "text-red-600 text-xs"
                        }
                    >
                        {ind.pass ? "✓" : "✗"}
                    </span>
                ))}
            </div>
            <CopyToClipboardButton
                text={cand.host}
                successMessage={t(
                    "page.nodes.sni-suggest.copied",
                    "SNI copied to clipboard",
                )}
                tooltipMsg={t("page.nodes.sni-suggest.copy_sni", "Copy SNI")}
            />
        </div>
    );
};
