import { type FC, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import {
    Button,
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from "@marzneshin/common/components";

import type {
    CheckoutChannelId,
    PaymentChannel,
} from "../../types";

/*
 * Checkout payment picker.
 *
 * Two top-level tabs: 易支付 (EPay) and USDT (TRC20). The EPay tab
 * lists every enabled 码商 row; the user picks one before clicking
 * "Pay". TRC20 has no sub-selection — there's exactly one
 * operator-configured receive address.
 *
 * The `trc20` pseudo-row is detected by `channel_code === "trc20"`
 * and excluded from the EPay tab; see user/fixtures.ts for the
 * synthesizing logic note.
 */

interface CheckoutPaymentPickerProps {
    channels: PaymentChannel[];
    onPay: (channelId: CheckoutChannelId) => void;
    pending: boolean;
}

export const CheckoutPaymentPicker: FC<CheckoutPaymentPickerProps> = ({
    channels,
    onPay,
    pending,
}) => {
    const { t } = useTranslation();

    const epayChannels = useMemo(
        () =>
            channels
                .filter((c) => c.enabled && c.channel_code !== "trc20")
                .sort((a, b) => b.priority - a.priority),
        [channels],
    );
    const trc20Available = channels.some(
        (c) => c.channel_code === "trc20" && c.enabled,
    );

    const [selectedEpay, setSelectedEpay] = useState<string>(
        epayChannels[0]?.channel_code ?? "",
    );

    const handleEpayPay = () => {
        if (!selectedEpay) return;
        onPay(`epay:${selectedEpay}`);
    };

    return (
        <Tabs defaultValue={epayChannels.length > 0 ? "epay" : "trc20"}>
            <TabsList className="grid grid-cols-2">
                <TabsTrigger value="epay" disabled={epayChannels.length === 0}>
                    {t("page.billing.purchase.picker.epay_tab")}
                </TabsTrigger>
                <TabsTrigger value="trc20" disabled={!trc20Available}>
                    {t("page.billing.purchase.picker.trc20_tab")}
                </TabsTrigger>
            </TabsList>

            <TabsContent value="epay" className="flex flex-col gap-3 pt-3">
                {epayChannels.length === 0 ? (
                    <div className="text-sm text-muted-foreground p-3 border rounded-md">
                        {t("page.billing.purchase.picker.epay_empty")}
                    </div>
                ) : (
                    <div className="flex flex-col gap-2">
                        {epayChannels.map((c) => (
                            <label
                                key={c.channel_code}
                                className="flex flex-row items-center gap-2 p-2 border rounded-md cursor-pointer hover:bg-muted/50"
                            >
                                <input
                                    type="radio"
                                    name="epay-channel"
                                    value={c.channel_code}
                                    checked={selectedEpay === c.channel_code}
                                    onChange={() =>
                                        setSelectedEpay(c.channel_code)
                                    }
                                />
                                <span className="flex-1">{c.display_name}</span>
                                <span className="text-xs text-muted-foreground font-mono">
                                    {c.channel_code}
                                </span>
                            </label>
                        ))}
                    </div>
                )}
                <Button
                    onClick={handleEpayPay}
                    disabled={pending || !selectedEpay}
                    className="w-full"
                >
                    {pending
                        ? t("page.billing.purchase.picker.paying")
                        : t("page.billing.purchase.picker.pay_epay")}
                </Button>
            </TabsContent>

            <TabsContent value="trc20" className="flex flex-col gap-3 pt-3">
                <p className="text-sm text-muted-foreground">
                    {t("page.billing.purchase.picker.trc20_desc")}
                </p>
                <Button
                    onClick={() => onPay("trc20")}
                    disabled={pending || !trc20Available}
                    className="w-full"
                >
                    {pending
                        ? t("page.billing.purchase.picker.paying")
                        : t("page.billing.purchase.picker.pay_trc20")}
                </Button>
            </TabsContent>
        </Tabs>
    );
};
