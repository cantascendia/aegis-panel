import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import i18n from "@marzneshin/features/i18n";
import { fetch, queryClient } from "@marzneshin/common/utils";

import type { Plan, PlanPatch } from "../types";
import { BillingPlansQueryKey } from "./plans.query";

interface UpdateArgs {
    id: number;
    patch: PlanPatch;
}

export async function fetchUpdatePlan({
    id,
    patch,
}: UpdateArgs): Promise<Plan> {
    return fetch<Plan>(`/billing/admin/plans/${id}`, {
        method: "patch",
        body: patch,
    });
}

const handleError = (error: Error) => {
    toast.error(
        i18n.t("page.billing.plans.toast.update_error", "Update failed"),
        { description: error.message },
    );
};

const handleSuccess = (plan: Plan) => {
    toast.success(
        i18n.t(
            "page.billing.plans.toast.update_success",
            "Plan {{code}} updated",
            { code: plan.operator_code },
        ),
    );
    queryClient.invalidateQueries({ queryKey: [BillingPlansQueryKey] });
};

export const useUpdatePlan = () =>
    useMutation({
        mutationKey: [BillingPlansQueryKey, "update"],
        mutationFn: fetchUpdatePlan,
        onError: handleError,
        onSuccess: handleSuccess,
    });
