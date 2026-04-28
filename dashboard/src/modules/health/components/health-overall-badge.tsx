import { type FC } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@marzneshin/common/components";
import { cn } from "@marzneshin/common/utils";

import type { HealthStatus } from "../types";

/*
 * Top-level overall status pill.
 *
 * Backend aggregates worst-of across subsystems (`aggregate_status` in
 * hardening/health/models.py). Visual mapping:
 *   ok       → green ("positive" badge variant) — quiet
 *   degraded → amber ("warning") — animated pulse so it catches the
 *              eye on a glanceable dashboard without blocking work
 *   down     → red ("destructive") — also pulses, harder
 *
 * Per L-017: friendly t() keys are extracted to consts before JSX so
 * the drift-gate regex sees them as `t("page.health.overall.<x>")`.
 */

const variantFor = (
    status: HealthStatus,
): "positive" | "warning" | "destructive" => {
    if (status === "ok") return "positive";
    if (status === "degraded") return "warning";
    return "destructive";
};

const labelFor = (status: HealthStatus, t: (k: string) => string): string => {
    if (status === "ok") return t("page.health.overall.green");
    if (status === "degraded") return t("page.health.overall.yellow");
    return t("page.health.overall.red");
};

export interface HealthOverallBadgeProps {
    status: HealthStatus;
}

export const HealthOverallBadge: FC<HealthOverallBadgeProps> = ({
    status,
}) => {
    const { t } = useTranslation();
    const shouldPulse = status !== "ok";
    return (
        <Badge
            variant={variantFor(status)}
            className={cn(
                "text-sm",
                shouldPulse && "animate-pulse",
            )}
        >
            {labelFor(status, t)}
        </Badge>
    );
};
