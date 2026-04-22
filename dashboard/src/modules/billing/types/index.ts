/*
 * Types for ops/billing/ backend.
 *
 * Mirrors the Pydantic response shapes from
 * ops/billing/schemas.py. Keep in sync when those change — there's
 * no auto-generation yet (a future A.5/v0.3 chore).
 */

export type PlanKind =
    | "fixed"
    | "flexible_traffic"
    | "flexible_duration";

export interface Plan {
    id: number;
    operator_code: string;
    display_name_en: string;
    display_name_i18n: Record<string, string>;
    kind: PlanKind;
    data_limit_gb: number | null;
    duration_days: number | null;
    price_cny_fen: number;
    enabled: boolean;
    sort_order: number;
    created_at: string;
}

export interface PlanIn {
    operator_code: string;
    display_name_en: string;
    display_name_i18n?: Record<string, string>;
    kind: PlanKind;
    data_limit_gb?: number | null;
    duration_days?: number | null;
    price_cny_fen: number;
    enabled?: boolean;
    sort_order?: number;
}

export interface PlanPatch {
    display_name_en?: string;
    display_name_i18n?: Record<string, string>;
    data_limit_gb?: number | null;
    duration_days?: number | null;
    price_cny_fen?: number;
    enabled?: boolean;
    sort_order?: number;
}
