/**
 * QuickPlans — operator UX (AEGIS fork wave-9 PR #179).
 *
 * Pre-fills the user creation form with one of the 4 standard plans
 * (trial / m1 / q1 / y1) so the operator doesn't have to manually
 * compute data_limit + expire_date for every customer.
 *
 * The plans MUST stay in sync with `aegis-user` CLI on the VPS
 * (/usr/local/bin/aegis-user :: plan() function). Mismatch =
 * customer charged for one tier but gets another.
 */

import { type FC } from "react";
import { useFormContext } from "react-hook-form";
import { useTranslation } from "react-i18next";
import {
    Button,
    HStack,
} from "@marzneshin/common/components";

import { DATA_LIMIT_METRIC } from "../../../constants";

interface QuickPlan {
    code: string;
    label: string;
    days: number;
    gb: number;
    note: string;
}

const QUICK_PLANS: ReadonlyArray<QuickPlan> = [
    { code: "trial", label: "Trial 3d / 50GB", days: 3, gb: 50, note: "trial 3d 50GB" },
    { code: "m1", label: "¥30 月 / 100GB", days: 30, gb: 100, note: "m1 ¥30/月_100GB" },
    { code: "q1", label: "¥80 季 / 300GB", days: 90, gb: 300, note: "q1 ¥80/季_300GB" },
    { code: "y1", label: "¥240 年 / 1.2TB", days: 365, gb: 1228, note: "y1 ¥240/年_1.2TB" },
];

const isoDateInDays = (days: number): string => {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() + days);
    // YYYY-MM-DDTHH:MM:SS without trailing Z (matches panel API expectation).
    return d.toISOString().replace(/\.\d{3}Z$/, "");
};

export const QuickPlans: FC = () => {
    const { t } = useTranslation();
    const form = useFormContext();

    const apply = (plan: QuickPlan) => {
        form.setValue("data_limit", plan.gb * DATA_LIMIT_METRIC, {
            shouldDirty: true, shouldTouch: true, shouldValidate: true,
        });
        form.setValue("data_limit_reset_strategy", "no_reset", {
            shouldDirty: true, shouldTouch: true, shouldValidate: true,
        });
        form.setValue("expire_strategy", "fixed_date", {
            shouldDirty: true, shouldTouch: true, shouldValidate: true,
        });
        form.setValue("expire_date", isoDateInDays(plan.days), {
            shouldDirty: true, shouldTouch: true, shouldValidate: true,
        });
        // Append plan note (don't overwrite operator's existing note)
        const existingNote = (form.getValues("note") as string | undefined) ?? "";
        const newNote = existingNote.includes(plan.note)
            ? existingNote
            : (existingNote ? `${existingNote} | ${plan.note}` : plan.note);
        form.setValue("note", newNote, {
            shouldDirty: true, shouldTouch: true, shouldValidate: true,
        });
    };

    return (
        <div className="space-y-2">
            <div className="text-sm font-medium text-muted-foreground">
                {t("page.users.quick_plans", "Quick Plans (one-click)")}
            </div>
            <HStack className="flex-wrap gap-2">
                {QUICK_PLANS.map((p) => (
                    <Button
                        key={p.code}
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => apply(p)}
                        className="text-xs"
                    >
                        {p.label}
                    </Button>
                ))}
            </HStack>
        </div>
    );
};
