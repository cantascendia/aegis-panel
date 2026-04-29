import { type FC } from "react";
import { useTranslation } from "react-i18next";

import {
    Badge,
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    Loading,
    ScrollArea,
} from "@marzneshin/common/components";

import { useAuditEvent } from "../api";
import type { AuditResult } from "../types";

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    eventId: number | null;
}

const resultVariant = (
    result: AuditResult,
): "default" | "secondary" | "destructive" => {
    if (result === "success") return "default";
    if (result === "denied") return "destructive";
    return "secondary";
};

const JsonBlock: FC<{ data: Record<string, unknown> | null }> = ({ data }) => {
    if (!data) return <span className="text-muted-foreground italic">—</span>;
    return (
        <pre className="text-xs font-mono bg-muted p-3 rounded-md overflow-auto max-h-60">
            {JSON.stringify(data, null, 2)}
        </pre>
    );
};

export const AuditEventDetailSheet: FC<Props> = ({
    open,
    onOpenChange,
    eventId,
}) => {
    const { t } = useTranslation();
    const { data: event, isLoading, isError } = useAuditEvent(eventId, {
        enabled: open && eventId !== null,
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>
                        {t("page.audit.detail.title")}{" "}
                        {eventId !== null && (
                            <span className="font-mono text-sm">#{eventId}</span>
                        )}
                    </DialogTitle>
                    <DialogDescription>
                        {t("page.audit.detail.subtitle")}
                    </DialogDescription>
                </DialogHeader>

                {isLoading && <Loading />}
                {isError && (
                    <div className="text-sm text-destructive">
                        {t("page.audit.detail.load_error")}
                    </div>
                )}

                {event && (
                    <ScrollArea className="max-h-[70vh]">
                        <div className="flex flex-col gap-4 pr-4">
                            {/* Summary row */}
                            <div className="grid grid-cols-2 gap-2 text-sm">
                                <div>
                                    <span className="text-muted-foreground">
                                        {t("page.audit.col.ts")}
                                    </span>
                                    <p className="font-mono">
                                        {new Date(event.ts).toLocaleString()}
                                    </p>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">
                                        {t("page.audit.col.result")}
                                    </span>
                                    <p>
                                        <Badge variant={resultVariant(event.result)}>
                                            {event.result}
                                        </Badge>
                                        <span className="ml-2 text-muted-foreground">
                                            HTTP {event.status_code}
                                        </span>
                                    </p>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">
                                        {t("page.audit.col.actor")}
                                    </span>
                                    <p className="font-mono">
                                        {event.actor_username ?? event.actor_type}
                                        {" "}
                                        <span className="text-xs text-muted-foreground">
                                            ({event.actor_type})
                                        </span>
                                    </p>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">IP</span>
                                    <p className="font-mono text-xs">{event.ip}</p>
                                </div>
                                <div className="col-span-2">
                                    <span className="text-muted-foreground">
                                        {t("page.audit.col.action")}
                                    </span>
                                    <p className="font-mono text-xs break-all">
                                        {event.action}
                                    </p>
                                </div>
                                {event.error_message && (
                                    <div className="col-span-2">
                                        <span className="text-muted-foreground">
                                            {t("page.audit.detail.error")}
                                        </span>
                                        <p className="text-xs text-destructive">
                                            {event.error_message}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Before / after state */}
                            <div className="flex flex-col gap-2">
                                <p className="text-sm font-medium">
                                    {t("page.audit.detail.before_state")}
                                </p>
                                <JsonBlock data={event.before_state} />
                            </div>
                            <div className="flex flex-col gap-2">
                                <p className="text-sm font-medium">
                                    {t("page.audit.detail.after_state")}
                                </p>
                                <JsonBlock data={event.after_state} />
                            </div>
                        </div>
                    </ScrollArea>
                )}
            </DialogContent>
        </Dialog>
    );
};
