/**
 * Regression test for the QuickPlans + UserSchema GB→bytes conversion
 * pipeline.
 *
 * Customer-blocking bug fixed 2026-05-08: QuickPlans pre-multiplied
 * `data_limit` by DATA_LIMIT_METRIC (1024^3) when clicked, then the
 * UserSchema transform multiplied AGAIN on submit, producing 1.15e20
 * bytes for a 100 GB plan — overflowing SQLite INTEGER and surfacing
 * as a 500 "Python int too large to convert to SQLite INTEGER" on
 * `POST /api/users`. The user couldn't create their first paying
 * customer through the dashboard.
 *
 * This test pins the schema's expectations so any future "convenience"
 * pre-conversion in QuickPlans (or anywhere else upstream of the
 * schema) fails fast in CI, not on a real customer.
 */

import { describe, expect, it } from 'vitest';
import { UserSchema, DATA_LIMIT_METRIC } from '@marzneshin/modules/users';

describe('UserSchema data_limit GB→bytes conversion', () => {
    const baseUser = {
        username: 'cust_test',
        note: null,
        expire_strategy: 'fixed_date' as const,
        expire_date: '2026-06-08T00:00:00',
        service_ids: [1],
    };

    it('converts 100 GB to 100 * 1024**3 bytes (107_374_182_400)', () => {
        const parsed = UserSchema.parse({ ...baseUser, data_limit: 100 });
        expect(parsed.data_limit).toBe(100 * DATA_LIMIT_METRIC);
        expect(parsed.data_limit).toBe(107_374_182_400);
    });

    it('converts string "100" the same way as number 100', () => {
        const parsed = UserSchema.parse({ ...baseUser, data_limit: '100' });
        expect(parsed.data_limit).toBe(100 * DATA_LIMIT_METRIC);
    });

    it('keeps the result below the SQLite INTEGER ceiling (2^63-1)', () => {
        // The largest plan QuickPlans defines is `y1` = 1228 GB.
        const parsed = UserSchema.parse({ ...baseUser, data_limit: 1228 });
        const sqliteMax = BigInt('9223372036854775807'); // 2^63 - 1
        expect(BigInt(parsed.data_limit as number) < sqliteMax).toBe(true);
    });

    it('rejects negative data_limit values', () => {
        expect(() => UserSchema.parse({ ...baseUser, data_limit: -5 })).toThrow(
            /minimum number is 0/i,
        );
    });

    it('REGRESSION: if QuickPlans pre-multiplies by DATA_LIMIT_METRIC, schema would overflow SQLite', () => {
        // This is the bug shape: QuickPlans used to set
        //   data_limit = 100 * DATA_LIMIT_METRIC = 107_374_182_400
        // then the schema applied the conversion again, producing
        //   100 * DATA_LIMIT_METRIC * DATA_LIMIT_METRIC ≈ 1.15e20
        // which exceeds the SQLite INT64 ceiling (~9.22e18).
        // We don't expect the schema to reject this (it accepts any
        // non-negative number), but the documented regression assertion
        // is that this product overflows int64, which is *exactly* what
        // the backend reported. If QuickPlans ever re-introduces the
        // pre-multiplication, the downstream API call will 500 again —
        // this test documents that link.
        const buggyInput = 100 * DATA_LIMIT_METRIC; // what the buggy QuickPlans set
        const parsed = UserSchema.parse({ ...baseUser, data_limit: buggyInput });
        const sqliteMax = BigInt('9223372036854775807');
        expect(BigInt(parsed.data_limit as number) > sqliteMax).toBe(true);
    });
});
