import { type FC, useEffect, useState } from "react";
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
    Input,
    Label,
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    Switch,
} from "@marzneshin/common/components";

import { useCreatePlan, useUpdatePlan } from "../api";
import type { Plan, PlanIn, PlanKind } from "../types";

/*
 * PlanFormDialog — create or edit a billing plan.
 *
 * Prop ``plan`` decides mode:
 *   - null/undefined → create, calls useCreatePlan
 *   - Plan object → edit, calls useUpdatePlan (PATCH partial)
 *
 * Field visibility adapts to ``kind`` to mirror the backend
 * Pydantic invariants (flexible_traffic uses GB only,
 * flexible_duration uses days only). Saves both dimensions for
 * fixed plans.
 *
 * Price input takes CNY in integer yuan (with optional decimals);
 * we convert to/from fen at submit/load time so the operator
 * doesn't have to mentally multiply by 100.
 */

const KIND_VALUES: PlanKind[] = [
    "fixed",
    "flexible_traffic",
    "flexible_duration",
];

interface PlanFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    plan?: Plan | null;
}

export const PlanFormDialog: FC<PlanFormDialogProps> = ({
    open,
    onOpenChange,
    plan,
}) => {
    const { t } = useTranslation();
    const createMutation = useCreatePlan();
    const updateMutation = useUpdatePlan();
    const editing = !!plan;

    const [operatorCode, setOperatorCode] = useState("");
    const [displayName, setDisplayName] = useState("");
    const [kind, setKind] = useState<PlanKind>("fixed");
    const [dataGb, setDataGb] = useState<string>("");
    const [days, setDays] = useState<string>("");
    const [priceYuan, setPriceYuan] = useState<string>("");
    const [enabled, setEnabled] = useState(true);

    useEffect(() => {
        if (!open) return;
        if (plan) {
            setOperatorCode(plan.operator_code);
            setDisplayName(plan.display_name_en);
            setKind(plan.kind);
            setDataGb(
                plan.data_limit_gb === null ? "" : String(plan.data_limit_gb),
            );
            setDays(
                plan.duration_days === null ? "" : String(plan.duration_days),
            );
            setPriceYuan((plan.price_cny_fen / 100).toFixed(2));
            setEnabled(plan.enabled);
        } else {
            setOperatorCode("");
            setDisplayName("");
            setKind("fixed");
            setDataGb("");
            setDays("");
            setPriceYuan("");
            setEnabled(true);
        }
    }, [open, plan]);

    const onSubmit = async () => {
        const priceFen = Math.round(Number(priceYuan) * 100);
        if (!Number.isFinite(priceFen) || priceFen < 0) return;

        const gbValue = dataGb === "" ? null : Math.max(0, Number(dataGb));
        const daysValue = days === "" ? null : Math.max(0, Number(days));

        if (editing && plan) {
            await updateMutation.mutateAsync({
                id: plan.id,
                patch: {
                    display_name_en: displayName,
                    data_limit_gb: gbValue,
                    duration_days: daysValue,
                    price_cny_fen: priceFen,
                    enabled,
                },
            });
        } else {
            const body: PlanIn = {
                operator_code: operatorCode,
                display_name_en: displayName,
                kind,
                data_limit_gb: gbValue,
                duration_days: daysValue,
                price_cny_fen: priceFen,
                enabled,
            };
            await createMutation.mutateAsync(body);
        }
        onOpenChange(false);
    };

    const showGb = kind === "fixed" || kind === "flexible_traffic";
    const showDays = kind === "fixed" || kind === "flexible_duration";
    const pending = createMutation.isPending || updateMutation.isPending;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>
                        {editing
                            ? t("page.billing.plans.dialog.edit_title")
                            : t("page.billing.plans.dialog.create_title")}
                    </DialogTitle>
                    <DialogDescription>
                        {t("page.billing.plans.dialog.desc")}
                    </DialogDescription>
                </DialogHeader>

                <div className="flex flex-col gap-3">
                    <div className="flex flex-col gap-1">
                        <Label htmlFor="plan-code">
                            {t("page.billing.plans.field.operator_code")}
                        </Label>
                        <Input
                            id="plan-code"
                            value={operatorCode}
                            onChange={(e) => setOperatorCode(e.target.value)}
                            placeholder="starter-30"
                            disabled={editing}
                        />
                        {editing && (
                            <p className="text-xs text-muted-foreground">
                                {t("page.billing.plans.field.operator_code_lock")}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-col gap-1">
                        <Label htmlFor="plan-name">
                            {t("page.billing.plans.field.display_name_en")}
                        </Label>
                        <Input
                            id="plan-name"
                            value={displayName}
                            onChange={(e) => setDisplayName(e.target.value)}
                            placeholder="Starter 30GB / 30 days"
                        />
                    </div>

                    <div className="flex flex-col gap-1">
                        <Label>
                            {t("page.billing.plans.field.kind")}
                        </Label>
                        <Select
                            value={kind}
                            onValueChange={(v) => setKind(v as PlanKind)}
                            disabled={editing}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {/* Kind option labels as explicit t() calls so the translations check can extract each key literally (template-literal keys are invisible to the regex). */}
                                <SelectItem value="fixed">
                                    {t("page.billing.plans.kind.fixed")}
                                </SelectItem>
                                <SelectItem value="flexible_traffic">
                                    {t("page.billing.plans.kind.flexible_traffic")}
                                </SelectItem>
                                <SelectItem value="flexible_duration">
                                    {t("page.billing.plans.kind.flexible_duration")}
                                </SelectItem>
                                {/* (KIND_VALUES preserved for potential future iteration needs) */}
                                {KIND_VALUES.length === 0 && null}
                            </SelectContent>
                        </Select>
                        {editing && (
                            <p className="text-xs text-muted-foreground">
                                {t("page.billing.plans.field.kind_lock")}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-row gap-2">
                        {showGb && (
                            <div className="flex flex-col gap-1 flex-1">
                                <Label htmlFor="plan-gb">
                                    {t("page.billing.plans.field.data_limit_gb")}
                                </Label>
                                <Input
                                    id="plan-gb"
                                    type="number"
                                    min={0}
                                    value={dataGb}
                                    onChange={(e) => setDataGb(e.target.value)}
                                />
                            </div>
                        )}
                        {showDays && (
                            <div className="flex flex-col gap-1 flex-1">
                                <Label htmlFor="plan-days">
                                    {t("page.billing.plans.field.duration_days")}
                                </Label>
                                <Input
                                    id="plan-days"
                                    type="number"
                                    min={0}
                                    value={days}
                                    onChange={(e) => setDays(e.target.value)}
                                />
                            </div>
                        )}
                    </div>

                    <div className="flex flex-row gap-2 items-end">
                        <div className="flex flex-col gap-1 flex-1">
                            <Label htmlFor="plan-price">
                                {t("page.billing.plans.field.price_cny")}
                            </Label>
                            <Input
                                id="plan-price"
                                type="number"
                                min={0}
                                step={0.01}
                                value={priceYuan}
                                onChange={(e) => setPriceYuan(e.target.value)}
                                placeholder="8.80"
                            />
                        </div>
                        <div className="flex flex-col gap-1 items-start">
                            <Label htmlFor="plan-enabled">
                                {t("page.billing.plans.field.enabled")}
                            </Label>
                            <div className="flex flex-row gap-2 items-center h-10">
                                <Switch
                                    id="plan-enabled"
                                    checked={enabled}
                                    onCheckedChange={setEnabled}
                                />
                                <Badge
                                    variant={enabled ? "default" : "secondary"}
                                >
                                    {enabled
                                        ? t("page.billing.plans.status.on")
                                        : t("page.billing.plans.status.off")}
                                </Badge>
                            </div>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        {t("cancel")}
                    </Button>
                    <Button
                        onClick={onSubmit}
                        disabled={
                            pending ||
                            !operatorCode ||
                            !displayName ||
                            priceYuan === ""
                        }
                    >
                        {pending
                            ? t("page.billing.plans.dialog.saving")
                            : t("submit")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
