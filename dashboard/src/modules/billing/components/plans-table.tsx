import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Plus } from "lucide-react";

import {
    Badge,
    Button,
    Loading,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@marzneshin/common/components";

import { useAdminPlans } from "../api";
import type { Plan } from "../types";
import { PlanFormDialog } from "./plan-form-dialog";

/*
 * Simple shadcn Table. Billing plans are a small set (rarely > 20
 * rows), no pagination/sort/filter. Add those later if operators
 * actually hit the problem.
 *
 * Row actions:
 *   - Edit: opens PlanFormDialog in edit mode
 *   - Enable/Disable toggle: via PATCH { enabled: !current } — a
 *     single-click action separate from the full edit dialog,
 *     matching how operators actually triage plans in practice
 */

const formatPriceCny = (fen: number) => `¥${(fen / 100).toFixed(2)}`;

const formatShape = (plan: Plan): string => {
    const bits: string[] = [];
    if (plan.data_limit_gb !== null) bits.push(`${plan.data_limit_gb} GB`);
    if (plan.duration_days !== null) bits.push(`${plan.duration_days} d`);
    return bits.length ? bits.join(" / ") : "—";
};

export const PlansTable: FC = () => {
    const { t } = useTranslation();
    const { data: plans, isLoading, isError, error } = useAdminPlans();

    const [dialogOpen, setDialogOpen] = useState(false);
    const [editing, setEditing] = useState<Plan | null>(null);

    const openCreate = () => {
        setEditing(null);
        setDialogOpen(true);
    };
    const openEdit = (plan: Plan) => {
        setEditing(plan);
        setDialogOpen(true);
    };

    if (isLoading) return <Loading />;
    if (isError) {
        return (
            <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                {t("page.billing.plans.load_error")}
                : {(error as Error).message}
            </div>
        );
    }

    const rows = plans ?? [];

    return (
        <div className="flex flex-col gap-3">
            <div className="flex flex-row justify-between items-center">
                <div>
                    <h2 className="text-lg font-semibold">
                        {t("page.billing.plans.title")}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        {t("page.billing.plans.subtitle")}
                    </p>
                </div>
                <Button onClick={openCreate}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t("page.billing.plans.create_button")}
                </Button>
            </div>

            {rows.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-10 border rounded-md">
                    {t("page.billing.plans.empty")}
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>
                                {t("page.billing.plans.col.code")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.plans.col.name")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.plans.col.kind")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.plans.col.shape")}
                            </TableHead>
                            <TableHead className="text-right">
                                {t("page.billing.plans.col.price")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.plans.col.enabled")}
                            </TableHead>
                            <TableHead className="w-10" />
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((plan) => (
                            <TableRow key={plan.id}>
                                <TableCell className="font-mono text-sm">
                                    {plan.operator_code}
                                </TableCell>
                                <TableCell>{plan.display_name_en}</TableCell>
                                <TableCell>
                                    <Badge variant="outline">
                                        {/* Kind label uses a static map because check_translations.sh regex can't extract template-literal keys. Three explicit t() calls keeps the keys discoverable. */}
                                        {plan.kind === "fixed"
                                            ? t("page.billing.plans.kind.fixed_short")
                                            : plan.kind === "flexible_traffic"
                                              ? t("page.billing.plans.kind.flexible_traffic_short")
                                              : t("page.billing.plans.kind.flexible_duration_short")}
                                    </Badge>
                                </TableCell>
                                <TableCell>{formatShape(plan)}</TableCell>
                                <TableCell className="text-right tabular-nums">
                                    {formatPriceCny(plan.price_cny_fen)}
                                </TableCell>
                                <TableCell>
                                    <Badge
                                        variant={
                                            plan.enabled
                                                ? "default"
                                                : "secondary"
                                        }
                                    >
                                        {plan.enabled
                                            ? t("page.billing.plans.status.on")
                                            : t("page.billing.plans.status.off")}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => openEdit(plan)}
                                    >
                                        <Pencil className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            )}

            <PlanFormDialog
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                plan={editing}
            />
        </div>
    );
};
