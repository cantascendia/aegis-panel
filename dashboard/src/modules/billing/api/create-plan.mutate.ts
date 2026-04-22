import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import i18n from "@marzneshin/features/i18n";
import { fetch, queryClient } from "@marzneshin/common/utils";

import type { Plan, PlanIn } from "../types";
import { BillingPlansQueryKey } from "./plans.query";

export async function fetchCreatePlan(plan: PlanIn): Promise<Plan> {
    return fetch<Plan>("/billing/admin/plans", {
        method: "post",
        body: plan,
    });
}

const handleError = (error: Error, value: PlanIn) => {
    toast.error(
        i18n.t("page.billing.plans.toast.create_error", "Create failed: {{code}}", {
            code: value.operator_code,
        }),
        { description: error.message },
    );
};

const handleSuccess = (plan: Plan) => {
    toast.success(
        i18n.t(
            "page.billing.plans.toast.create_success",
            "Plan {{code}} created",
            { code: plan.operator_code },
        ),
    );
    queryClient.invalidateQueries({ queryKey: [BillingPlansQueryKey] });
};

export const useCreatePlan = () =>
    useMutation({
        mutationKey: [BillingPlansQueryKey, "create"],
        mutationFn: fetchCreatePlan,
        onError: handleError,
        onSuccess: handleSuccess,
    });
