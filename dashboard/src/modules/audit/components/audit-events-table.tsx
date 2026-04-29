import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { Eye, Download } from "lucide-react";

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

import { useAuditEvents } from "../api";
import type { AuditEventRow, AuditResult } from "../types";
import { AuditEventDetailSheet } from "./audit-event-detail-sheet";

const formatTs = (iso: string) => new Date(iso).toLocaleString();

const resultBadge = (
    result: AuditResult,
): "default" | "secondary" | "destructive" => {
    if (result === "success") return "default";
    if (result === "denied") return "destructive";
    return "secondary";
};

const _EXPORT_URL = "/api/audit/events/export.csv";

export const AuditEventsTable: FC = () => {
    const { t } = useTranslation();

    const [actorUsername, setActorUsername] = useState("");
    const [resultFilter, setResultFilter] = useState<AuditResult | "">("");
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [sheetOpen, setSheetOpen] = useState(false);

    const { data: events, isLoading, isError, error } = useAuditEvents({
        actor_username: actorUsername.trim() || undefined,
        result: resultFilter || undefined,
        limit: 100,
    });

    const openDetail = (ev: AuditEventRow) => {
        setSelectedId(ev.id);
        setSheetOpen(true);
    };

    return (
        <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold">
                        {t("page.audit.title")}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        {t("page.audit.subtitle")}
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    asChild
                >
                    <a href={_EXPORT_URL} download>
                        <Download className="mr-2 h-4 w-4" />
                        {t("page.audit.export_csv")}
                    </a>
                </Button>
            </div>

            {/* Filters */}
            <div className="flex flex-row gap-2 items-end flex-wrap">
                <div className="flex flex-col gap-1 w-40">
                    <Label htmlFor="audit-actor">
                        {t("page.audit.filter.actor")}
                    </Label>
                    <Input
                        id="audit-actor"
                        value={actorUsername}
                        onChange={(e) => setActorUsername(e.target.value)}
                        placeholder="admin"
                    />
                </div>
                <div className="flex flex-col gap-1 w-36">
                    <Label htmlFor="audit-result">
                        {t("page.audit.filter.result")}
                    </Label>
                    <Select
                        value={resultFilter === "" ? "__any" : resultFilter}
                        onValueChange={(v) =>
                            setResultFilter(
                                v === "__any" ? "" : (v as AuditResult),
                            )
                        }
                    >
                        <SelectTrigger id="audit-result">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="__any">
                                {t("page.audit.filter.result_any")}
                            </SelectItem>
                            <SelectItem value="success">success</SelectItem>
                            <SelectItem value="failure">failure</SelectItem>
                            <SelectItem value="denied">denied</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {isLoading && <Loading />}
            {isError && (
                <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                    {t("page.audit.load_error")}:{" "}
                    {(error as Error).message}
                </div>
            )}

            {events && events.length === 0 && (
                <div className="text-sm text-muted-foreground text-center py-10 border rounded-md">
                    {t("page.audit.empty")}
                </div>
            )}

            {events && events.length > 0 && (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-16">#</TableHead>
                            <TableHead>{t("page.audit.col.ts")}</TableHead>
                            <TableHead>{t("page.audit.col.actor")}</TableHead>
                            <TableHead>{t("page.audit.col.action")}</TableHead>
                            <TableHead>{t("page.audit.col.result")}</TableHead>
                            <TableHead className="w-10" />
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {events.map((ev) => (
                            <TableRow key={ev.id}>
                                <TableCell className="font-mono text-xs text-muted-foreground">
                                    {ev.id}
                                </TableCell>
                                <TableCell className="text-xs whitespace-nowrap">
                                    {formatTs(ev.ts)}
                                </TableCell>
                                <TableCell className="font-mono text-xs">
                                    {ev.actor_username ?? (
                                        <span className="text-muted-foreground italic">
                                            {ev.actor_type}
                                        </span>
                                    )}
                                </TableCell>
                                <TableCell className="font-mono text-xs max-w-xs truncate">
                                    {ev.action}
                                </TableCell>
                                <TableCell>
                                    <Badge variant={resultBadge(ev.result)}>
                                        {ev.result}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => openDetail(ev)}
                                    >
                                        <Eye className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            )}

            <AuditEventDetailSheet
                open={sheetOpen}
                onOpenChange={setSheetOpen}
                eventId={selectedId}
            />
        </div>
    );
};
