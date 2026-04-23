import { type FC, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, Save, ShieldAlert, Unlock } from "lucide-react";
import {
    Badge,
    Button,
    Input,
    Label,
    ScrollArea,
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    Separator,
    Skeleton,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
    Textarea,
} from "@marzneshin/common/components";
import {
    type IpLimitAction,
    type IpLimitState,
    useIpLimitAuditQuery,
    useIpLimitDisableClearMutation,
    useIpLimitOverrideMutation,
    useIpLimitQuery,
} from "@marzneshin/modules/users";

interface UserIpLimitSectionProps {
    username: string;
}

export const UserIpLimitSection: FC<UserIpLimitSectionProps> = ({
    username,
}) => {
    const { t } = useTranslation();
    const stateQuery = useIpLimitQuery({ username });
    const auditQuery = useIpLimitAuditQuery({ username });
    const mutation = useIpLimitOverrideMutation();
    const clearMutation = useIpLimitDisableClearMutation();

    if (stateQuery.isPending) {
        return (
            <div className="flex flex-col gap-3 p-2">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-40 w-full" />
            </div>
        );
    }

    if (stateQuery.error || !stateQuery.data) {
        return (
            <div className="text-sm text-destructive p-3">
                {t(
                    "page.users.iplimit.error",
                    "IP limiter state could not be loaded.",
                )}
            </div>
        );
    }

    const onRefresh = () => {
        stateQuery.refetch();
        auditQuery.refetch();
    };

    return (
        <div className="flex flex-col gap-4 p-1">
            <RuntimeState
                state={stateQuery.data}
                clearing={clearMutation.isPending}
                onClear={() => clearMutation.mutate({ username })}
                onRefresh={onRefresh}
            />
            <OverrideForm
                state={stateQuery.data}
                saving={mutation.isPending}
                onSave={(values) => mutation.mutate(values)}
            />
            <AuditLog
                events={auditQuery.data?.events ?? []}
                isPending={auditQuery.isPending}
            />
        </div>
    );
};

interface RuntimeStateProps {
    state: IpLimitState;
    clearing: boolean;
    onClear: () => void;
    onRefresh: () => void;
}

const RuntimeState: FC<RuntimeStateProps> = ({
    state,
    clearing,
    onClear,
    onRefresh,
}) => {
    const { t } = useTranslation();
    const disabledUntil = state.disabled_until
        ? new Date(state.disabled_until * 1000).toLocaleString()
        : null;

    return (
        <section className="rounded-md border p-3">
            <div className="flex flex-row items-center justify-between gap-2">
                <div className="flex flex-row items-center gap-2">
                    <ShieldAlert className="size-5 text-muted-foreground" />
                    <div>
                        <h3 className="text-sm font-medium">
                            {t(
                                "page.users.iplimit.runtime.title",
                                "IP limiter",
                            )}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                            {state.redis_configured
                                ? t(
                                      "page.users.iplimit.runtime.enabled",
                                      "{{count}} IPs in the active window",
                                      { count: state.observed_count },
                                  )
                                : t(
                                      "page.users.iplimit.runtime.redis_disabled",
                                      "Redis is not configured; runtime tracking is disabled.",
                                  )}
                        </p>
                    </div>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                    {disabledUntil && (
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={onClear}
                            disabled={clearing}
                        >
                            <Unlock className="mr-2 size-4" />
                            {clearing
                                ? t(
                                      "page.users.iplimit.runtime.clearing",
                                      "Clearing...",
                                  )
                                : t(
                                      "page.users.iplimit.runtime.clear_disable",
                                      "Clear disable",
                                  )}
                        </Button>
                    )}
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={onRefresh}
                    >
                        <RefreshCw className="mr-2 size-4" />
                        {t("page.users.iplimit.refresh", "Refresh")}
                    </Button>
                </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
                {state.observed_ips.length > 0 ? (
                    state.observed_ips.map((ip) => (
                        <Badge key={ip} variant="secondary">
                            {ip}
                        </Badge>
                    ))
                ) : (
                    <span className="text-xs text-muted-foreground">
                        {t(
                            "page.users.iplimit.runtime.no_ips",
                            "No IPs observed in the current window.",
                        )}
                    </span>
                )}
            </div>

            {disabledUntil && (
                <div className="mt-3 text-xs text-destructive">
                    {t(
                        "page.users.iplimit.runtime.disabled_until",
                        "Temporarily disabled until {{time}}",
                        { time: disabledUntil },
                    )}
                </div>
            )}
        </section>
    );
};

interface OverrideFormProps {
    state: IpLimitState;
    saving: boolean;
    onSave: (values: {
        username: string;
        max_concurrent_ips: number | null;
        window_seconds: number | null;
        violation_action: IpLimitAction | null;
        ip_allowlist_cidrs: string | null;
    }) => void;
}

const OverrideForm: FC<OverrideFormProps> = ({ state, saving, onSave }) => {
    const { t } = useTranslation();
    const [maxIps, setMaxIps] = useState<string>("");
    const [windowSeconds, setWindowSeconds] = useState<string>("");
    const [allowlistCidrs, setAllowlistCidrs] = useState<string>("");
    const [action, setAction] = useState<IpLimitAction | "inherit">("inherit");

    useEffect(() => {
        setMaxIps(state.override?.max_concurrent_ips?.toString() ?? "");
        setWindowSeconds(state.override?.window_seconds?.toString() ?? "");
        setAllowlistCidrs(state.override?.ip_allowlist_cidrs ?? "");
        setAction(state.override?.violation_action ?? "inherit");
    }, [state.override]);

    const effective = state.config;
    const onSubmit = () => {
        onSave({
            username: state.username,
            max_concurrent_ips: maxIps ? Number(maxIps) : null,
            window_seconds: windowSeconds ? Number(windowSeconds) : null,
            violation_action: action === "inherit" ? null : action,
            ip_allowlist_cidrs: allowlistCidrs,
        });
    };

    return (
        <section className="rounded-md border p-3">
            <div className="grid gap-3 md:grid-cols-3">
                <div className="flex flex-col gap-1">
                    <Label htmlFor="iplimit-max">
                        {t(
                            "page.users.iplimit.override.max_ips",
                            "Max concurrent IPs",
                        )}
                    </Label>
                    <Input
                        id="iplimit-max"
                        type="number"
                        min={1}
                        placeholder={String(effective.max_concurrent_ips)}
                        value={maxIps}
                        onChange={(e) => setMaxIps(e.target.value)}
                    />
                </div>
                <div className="flex flex-col gap-1">
                    <Label htmlFor="iplimit-window">
                        {t(
                            "page.users.iplimit.override.window",
                            "Window seconds",
                        )}
                    </Label>
                    <Input
                        id="iplimit-window"
                        type="number"
                        min={30}
                        placeholder={String(effective.window_seconds)}
                        value={windowSeconds}
                        onChange={(e) => setWindowSeconds(e.target.value)}
                    />
                </div>
                <div className="flex flex-col gap-1">
                    <Label>
                        {t(
                            "page.users.iplimit.override.action",
                            "Violation action",
                        )}
                    </Label>
                    <Select
                        value={action}
                        onValueChange={(value) =>
                            setAction(value as IpLimitAction | "inherit")
                        }
                    >
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="inherit">
                                {t(
                                    "page.users.iplimit.override.inherit",
                                    "Inherit",
                                )}
                            </SelectItem>
                            <SelectItem value="warn">
                                {t("page.users.iplimit.action.warn", "Warn")}
                            </SelectItem>
                            <SelectItem value="disable">
                                {t(
                                    "page.users.iplimit.action.disable",
                                    "Disable",
                                )}
                            </SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>
            <div className="mt-3 flex flex-col gap-1">
                <Label htmlFor="iplimit-allowlist">
                    {t(
                        "page.users.iplimit.override.allowlist",
                        "Allowlisted CIDRs",
                    )}
                </Label>
                <Textarea
                    id="iplimit-allowlist"
                    className="min-h-24 font-mono text-xs"
                    placeholder={
                        effective.ip_allowlist_cidrs ||
                        "203.0.113.0/24\n2001:db8::/32"
                    }
                    value={allowlistCidrs}
                    onChange={(event) =>
                        setAllowlistCidrs(event.target.value)
                    }
                />
                <p className="text-xs text-muted-foreground">
                    {t(
                        "page.users.iplimit.override.allowlist_hint",
                        "One CIDR per line. Matching IPs are ignored before counting.",
                    )}
                </p>
            </div>
            <div className="mt-3 flex flex-row items-center justify-between gap-2">
                <p className="text-xs text-muted-foreground">
                    {t(
                        "page.users.iplimit.override.effective",
                        "Empty fields inherit the global policy.",
                    )}
                </p>
                <Button
                    type="button"
                    size="sm"
                    onClick={onSubmit}
                    disabled={saving}
                >
                    <Save className="mr-2 size-4" />
                    {saving
                        ? t("page.users.iplimit.saving", "Saving...")
                        : t("page.users.iplimit.save", "Save")}
                </Button>
            </div>
        </section>
    );
};

interface AuditLogProps {
    events: {
        ts: number;
        count: number;
        action: IpLimitAction;
        ip_list: string[];
    }[];
    isPending: boolean;
}

const AuditLog: FC<AuditLogProps> = ({ events, isPending }) => {
    const { t } = useTranslation();
    const rows = events.slice(0, 25);

    return (
        <section className="rounded-md border">
            <div className="p-3">
                <h3 className="text-sm font-medium">
                    {t("page.users.iplimit.audit.title", "Audit log")}
                </h3>
                <p className="text-xs text-muted-foreground">
                    {t(
                        "page.users.iplimit.audit.desc",
                        "Recent IP limit violations for this user.",
                    )}
                </p>
            </div>
            <Separator />
            {isPending ? (
                <div className="p-3">
                    <Skeleton className="h-20 w-full" />
                </div>
            ) : rows.length === 0 ? (
                <div className="p-3 text-xs text-muted-foreground">
                    {t(
                        "page.users.iplimit.audit.empty",
                        "No violations recorded.",
                    )}
                </div>
            ) : (
                <ScrollArea className="max-h-64">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>
                                    {t(
                                        "page.users.iplimit.audit.time",
                                        "Time",
                                    )}
                                </TableHead>
                                <TableHead>
                                    {t(
                                        "page.users.iplimit.audit.action",
                                        "Action",
                                    )}
                                </TableHead>
                                <TableHead>
                                    {t(
                                        "page.users.iplimit.audit.ips",
                                        "IPs",
                                    )}
                                </TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.map((event) => (
                                <TableRow key={`${event.ts}-${event.action}`}>
                                    <TableCell className="whitespace-nowrap">
                                        {new Date(
                                            event.ts * 1000,
                                        ).toLocaleString()}
                                    </TableCell>
                                    <TableCell>
                                        <Badge
                                            variant={
                                                event.action === "disable"
                                                    ? "destructive"
                                                    : "secondary"
                                            }
                                        >
                                            {event.action === "disable"
                                                ? t(
                                                      "page.users.iplimit.action.disable",
                                                      "Disable",
                                                  )
                                                : t(
                                                      "page.users.iplimit.action.warn",
                                                      "Warn",
                                                  )}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <span className="font-mono text-xs">
                                            {event.ip_list.join(", ")}
                                        </span>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </ScrollArea>
            )}
        </section>
    );
};
