import { type FC, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";

import {
    Button,
    Input,
    Label,
} from "@marzneshin/common/components";
import { fetch } from "@marzneshin/common/utils";

/*
 * UserSelector — debounced search-as-you-type combobox for picking
 * the user the operator is creating an invoice on behalf of.
 *
 * Fetches `GET /users?username=<typed>&size=20` (same endpoint
 * UsersTable uses, gated by admin auth like all admin pages).
 * Returns the local user with id + username so the parent's
 * checkout payload can include `user_id` per CheckoutIn schema.
 *
 * Why not lift into a fully-featured Combobox shadcn component:
 * shadcn `<Command>` is overkill here (we don't need keyboard nav
 * niceties); a plain Input + dropdown list is enough and avoids
 * adding the @radix-ui/react-popover dependency surface.
 */

interface PickedUser {
    id: number;
    username: string;
}

/** Minimal user shape the picker needs. Backend `/users` returns
 *  many more fields (UserType + id) but we only consume these two
 *  here to stay loosely coupled — no need to import the heavy
 *  UserType definition for a picker. */
interface UserListEntry {
    id: number;
    username: string;
}

interface UsersListResponse {
    items: UserListEntry[];
    pages: number;
}

const DEBOUNCE_MS = 250;
const PAGE_SIZE = 20;

interface UserSelectorProps {
    selected: PickedUser | null;
    onSelect: (user: PickedUser | null) => void;
}

export const UserSelector: FC<UserSelectorProps> = ({ selected, onSelect }) => {
    const { t } = useTranslation();
    const [input, setInput] = useState(selected?.username ?? "");
    const [debounced, setDebounced] = useState(input);
    const [openDropdown, setOpenDropdown] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Debounce input → debounced. 250ms feels live without thrashing
    // the backend — typing "alice" hits the API once, not 5 times.
    useEffect(() => {
        const id = setTimeout(() => setDebounced(input), DEBOUNCE_MS);
        return () => clearTimeout(id);
    }, [input]);

    // Close dropdown on outside click. `mousedown` (not `click`)
    // because we want to close BEFORE the input loses focus, so the
    // user can immediately tab/type next.
    useEffect(() => {
        const onDocClick = (e: MouseEvent) => {
            if (
                containerRef.current &&
                !containerRef.current.contains(e.target as Node)
            ) {
                setOpenDropdown(false);
            }
        };
        document.addEventListener("mousedown", onDocClick);
        return () => document.removeEventListener("mousedown", onDocClick);
    }, []);

    const { data, isFetching } = useQuery({
        queryKey: ["billing-user-selector-search", debounced],
        queryFn: async (): Promise<UsersListResponse> =>
            fetch<UsersListResponse>(`/users`, {
                query: {
                    username: debounced,
                    size: PAGE_SIZE,
                    page: 1,
                },
            }),
        // Don't fire the open-ended `username=` query (would return
        // first page of all users) — wait until the operator types
        // at least one char. Empty input still allowed if the
        // operator wants to see a recent slice; cheap.
        enabled: debounced.length >= 0,
        staleTime: 30_000,
    });

    const items = data?.items ?? [];
    // Extract long key to a const so the line-based extraction
    // regex in tools/check_translations.sh sees it intact (per L-017
    // — biome wraps long calls inside JSX attributes across lines).
    const inputPlaceholder = t("page.billing.purchase.user_selector.placeholder");

    const choose = (u: UserListEntry) => {
        onSelect({ id: u.id, username: u.username });
        setInput(u.username);
        setOpenDropdown(false);
    };

    const clear = () => {
        onSelect(null);
        setInput("");
        setOpenDropdown(true);
    };

    return (
        <div className="flex flex-col gap-1" ref={containerRef}>
            <Label htmlFor="billing-user-selector">
                {t("page.billing.purchase.user_selector.label")}
            </Label>
            <div className="relative">
                <Input
                    id="billing-user-selector"
                    type="text"
                    value={input}
                    placeholder={inputPlaceholder}
                    onChange={(e) => {
                        setInput(e.target.value);
                        setOpenDropdown(true);
                        // Clear selection if the operator changes
                        // the text away from the picked username —
                        // avoids stale (id, displayed name) skew.
                        if (selected && e.target.value !== selected.username) {
                            onSelect(null);
                        }
                    }}
                    onFocus={() => setOpenDropdown(true)}
                    autoComplete="off"
                />
                {selected && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-1 top-1 h-7"
                        onClick={clear}
                    >
                        {t("page.billing.purchase.user_selector.clear")}
                    </Button>
                )}

                {openDropdown && (
                    <div
                        className="absolute z-10 mt-1 w-full max-h-72 overflow-y-auto rounded-md border bg-popover shadow-md"
                    >
                        {isFetching && (
                            <div className="px-3 py-2 text-xs text-muted-foreground">
                                {t("page.billing.purchase.user_selector.searching")}
                            </div>
                        )}
                        {!isFetching && items.length === 0 && (
                            <div className="px-3 py-2 text-xs text-muted-foreground">
                                {t("page.billing.purchase.user_selector.no_results")}
                            </div>
                        )}
                        {items.map((u) => (
                            <button
                                key={u.id}
                                type="button"
                                onClick={() => choose(u)}
                                className="w-full px-3 py-2 text-left text-sm hover:bg-muted/60 focus:bg-muted/60 outline-none"
                            >
                                <span className="font-medium">{u.username}</span>
                                <span className="ml-2 text-xs text-muted-foreground font-mono">
                                    #{u.id}
                                </span>
                            </button>
                        ))}
                    </div>
                )}
            </div>
            {selected && (
                <p className="text-xs text-muted-foreground">
                    {t("page.billing.purchase.user_selector.selected_hint", {
                        defaultValue: "Selected: {{username}} (#{{id}})",
                        username: selected.username,
                        id: selected.id,
                    })}
                </p>
            )}
        </div>
    );
};
