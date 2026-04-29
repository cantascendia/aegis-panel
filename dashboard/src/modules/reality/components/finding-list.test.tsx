/**
 * Unit tests for FindingList.
 *
 * Locks the severity → bullet/text colour mapping and the
 * "score_delta=0 hides the delta tag" rule — both relied on by the
 * health-at-a-glance design.
 *
 * Coverage targets (issue #102 acceptance):
 *   - severity=critical → red bullet + red label text
 *   - severity=warning  → amber bullet + amber label text
 *   - severity=info     → muted bullet + muted label text
 *   - score_delta=0 → no delta tag rendered
 *   - score_delta < 0 → delta tag rendered (e.g. "-15")
 *   - empty findings array → empty state copy
 *
 * Bullet element is `aria-hidden`, so we locate it via its sibling
 * label text and traverse to the rounded-full span.
 */

import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import { renderWithProviders } from "@marzneshin/test-utils/render";

import type { Finding } from "../types";
import { FindingList } from "./finding-list";

function makeFinding(overrides: Partial<Finding> = {}): Finding {
    return {
        check: "sni_coldness",
        ok: true,
        severity: "info",
        score_delta: 0,
        evidence: "default evidence",
        remediation: "",
        data: {},
        ...overrides,
    };
}

/**
 * Bullet lives as a sibling preceding the label inside the same <li>.
 * We grab the label span and walk back to find the bullet for class
 * assertions.
 *
 * Note: `checkLabel` in the component returns the raw check name when
 * the i18n translation falls back to the key (which is what happens in
 * unit tests since locale JSON loads via HTTP backend). So the visible
 * label text is the bare check identifier, not `page.reality.check.X`.
 */
function findBulletByCheck(check: string): HTMLElement {
    const label = screen.getByText(check);
    const li = label.closest("li");
    if (!li) throw new Error(`could not find <li> for check=${check}`);
    const bullet = li.querySelector("span.rounded-full");
    if (!bullet) throw new Error(`bullet not found in li for ${check}`);
    return bullet as HTMLElement;
}

describe("FindingList", () => {
    it("maps severity=critical to a red bullet and red label", () => {
        renderWithProviders(
            <FindingList
                findings={[
                    makeFinding({
                        check: "port_canonical",
                        severity: "critical",
                        score_delta: -25,
                        evidence: "Port 8443 not canonical",
                    }),
                ]}
            />,
        );
        const bullet = findBulletByCheck("port_canonical");
        expect(bullet.className).toMatch(/bg-destructive/);
        const label = screen.getByText("port_canonical");
        expect(label.className).toMatch(/text-destructive/);
    });

    it("maps severity=warning to an amber bullet and amber label", () => {
        renderWithProviders(
            <FindingList
                findings={[
                    makeFinding({
                        check: "asn_match",
                        severity: "warning",
                        score_delta: -10,
                        evidence: "ASN mismatch",
                    }),
                ]}
            />,
        );
        const bullet = findBulletByCheck("asn_match");
        expect(bullet.className).toMatch(/bg-amber-500/);
        const label = screen.getByText("asn_match");
        expect(label.className).toMatch(/text-amber-600/);
    });

    it("maps severity=info to a muted bullet and muted label", () => {
        renderWithProviders(
            <FindingList
                findings={[
                    makeFinding({
                        check: "sni_coldness",
                        severity: "info",
                        score_delta: 0,
                        evidence: "SNI cold",
                    }),
                ]}
            />,
        );
        const bullet = findBulletByCheck("sni_coldness");
        expect(bullet.className).toMatch(/bg-muted-foreground/);
        const label = screen.getByText("sni_coldness");
        expect(label.className).toMatch(/text-muted-foreground/);
    });

    it("hides the score_delta tag when delta == 0", () => {
        renderWithProviders(
            <FindingList
                findings={[
                    makeFinding({
                        check: "sni_coldness",
                        severity: "info",
                        score_delta: 0,
                        evidence: "fine",
                    }),
                ]}
            />,
        );
        // The delta is rendered as a tabular-nums span if non-zero;
        // there should be no "0" or "-0" sitting next to the label.
        const label = screen.getByText("sni_coldness");
        const li = label.closest("li");
        expect(li).not.toBeNull();
        // No span with the delta-tag classes should exist for the
        // zero-delta finding.
        expect(li!.querySelector("span.tabular-nums")).toBeNull();
    });

    it("shows the score_delta tag for negative deltas (e.g. -15)", () => {
        renderWithProviders(
            <FindingList
                findings={[
                    makeFinding({
                        check: "shortid_compliance",
                        severity: "warning",
                        score_delta: -15,
                        evidence: "short id non-compliant",
                    }),
                ]}
            />,
        );
        // The delta tag renders the JS number toString → "-15".
        expect(screen.getByText("-15")).toBeInTheDocument();
    });

    it("renders the empty state copy when findings is []", () => {
        renderWithProviders(<FindingList findings={[]} />);
        expect(
            screen.getByText("page.reality.finding.empty"),
        ).toBeInTheDocument();
    });

    it("renders evidence and remediation lines when remediation is non-empty", () => {
        renderWithProviders(
            <FindingList
                findings={[
                    makeFinding({
                        check: "asn_match",
                        severity: "warning",
                        score_delta: -10,
                        evidence: "ASN drift on Cloudflare endpoint",
                        remediation: "Pin to a same-ASN SNI",
                    }),
                ]}
            />,
        );
        expect(
            screen.getByText("ASN drift on Cloudflare endpoint"),
        ).toBeInTheDocument();
        expect(
            screen.getByText("Pin to a same-ASN SNI"),
        ).toBeInTheDocument();
    });
});
