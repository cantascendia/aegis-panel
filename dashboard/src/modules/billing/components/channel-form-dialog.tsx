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
    Switch,
} from "@marzneshin/common/components";

import { useCreateChannel, useUpdateChannel } from "../api";
import type { PaymentChannel, PaymentChannelIn } from "../types";

/*
 * ChannelFormDialog — create or edit an EPay payment channel.
 *
 * ``channel`` prop decides mode:
 *   - null/undefined → create (requires secret_key)
 *   - PaymentChannel object → edit (secret_key optional; leaving
 *     blank keeps existing; providing rotates)
 *
 * ``channel_code`` is immutable after creation (backend treats it
 * as a stable identifier referenced in invoice provider strings
 * like ``epay:<channel_code>``).
 *
 * ``secret_key`` is NEVER shown (the backend omits it in
 * ChannelOut). The field is write-only; treat it as a password
 * rotation interface.
 */

interface ChannelFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    channel?: PaymentChannel | null;
}

export const ChannelFormDialog: FC<ChannelFormDialogProps> = ({
    open,
    onOpenChange,
    channel,
}) => {
    const { t } = useTranslation();
    const createMutation = useCreateChannel();
    const updateMutation = useUpdateChannel();
    const editing = !!channel;

    const [channelCode, setChannelCode] = useState("");
    const [displayName, setDisplayName] = useState("");
    const [gatewayUrl, setGatewayUrl] = useState("");
    const [merchantId, setMerchantId] = useState("");
    const [secretKey, setSecretKey] = useState("");
    const [priority, setPriority] = useState<string>("0");
    const [enabled, setEnabled] = useState(false);

    useEffect(() => {
        if (!open) return;
        if (channel) {
            setChannelCode(channel.channel_code);
            setDisplayName(channel.display_name);
            setGatewayUrl(channel.gateway_url);
            setMerchantId(channel.merchant_id);
            setSecretKey(""); // never prefill; edit mode treats blank = no change
            setPriority(String(channel.priority));
            setEnabled(channel.enabled);
        } else {
            setChannelCode("");
            setDisplayName("");
            setGatewayUrl("");
            setMerchantId("");
            setSecretKey("");
            setPriority("0");
            setEnabled(false);
        }
    }, [open, channel]);

    const onSubmit = async () => {
        const priorityVal = Math.floor(Number(priority) || 0);
        if (editing && channel) {
            await updateMutation.mutateAsync({
                id: channel.id,
                patch: {
                    display_name: displayName,
                    gateway_url: gatewayUrl,
                    merchant_id: merchantId,
                    ...(secretKey ? { secret_key: secretKey } : {}),
                    enabled,
                    priority: priorityVal,
                },
            });
        } else {
            const body: PaymentChannelIn = {
                channel_code: channelCode,
                display_name: displayName,
                kind: "epay",
                gateway_url: gatewayUrl,
                merchant_id: merchantId,
                secret_key: secretKey,
                enabled,
                priority: priorityVal,
            };
            await createMutation.mutateAsync(body);
        }
        onOpenChange(false);
    };

    const pending = createMutation.isPending || updateMutation.isPending;
    const submitDisabled =
        pending ||
        !channelCode ||
        !displayName ||
        !gatewayUrl ||
        !merchantId ||
        // secret_key is required on CREATE; on edit it's optional
        (!editing && !secretKey);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>
                        {editing
                            ? t("page.billing.channels.dialog.edit_title")
                            : t("page.billing.channels.dialog.create_title")}
                    </DialogTitle>
                    <DialogDescription>
                        {t("page.billing.channels.dialog.desc")}
                    </DialogDescription>
                </DialogHeader>

                <div className="flex flex-col gap-3">
                    <div className="flex flex-col gap-1">
                        <Label htmlFor="ch-code">
                            {t("page.billing.channels.field.channel_code")}
                        </Label>
                        <Input
                            id="ch-code"
                            value={channelCode}
                            onChange={(e) => setChannelCode(e.target.value)}
                            placeholder="zpay1"
                            disabled={editing}
                        />
                        {editing && (
                            <p className="text-xs text-muted-foreground">
                                {t("page.billing.channels.field.channel_code_lock")}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-col gap-1">
                        <Label htmlFor="ch-name">
                            {t("page.billing.channels.field.display_name")}
                        </Label>
                        <Input
                            id="ch-name"
                            value={displayName}
                            onChange={(e) => setDisplayName(e.target.value)}
                            placeholder="ZPay Main"
                        />
                    </div>

                    <div className="flex flex-col gap-1">
                        <Label htmlFor="ch-url">
                            {t("page.billing.channels.field.gateway_url")}
                        </Label>
                        <Input
                            id="ch-url"
                            value={gatewayUrl}
                            onChange={(e) => setGatewayUrl(e.target.value)}
                            placeholder="https://zpay.example/submit"
                        />
                    </div>

                    <div className="flex flex-row gap-2">
                        <div className="flex flex-col gap-1 flex-1">
                            <Label htmlFor="ch-merchant">
                                {t("page.billing.channels.field.merchant_id")}
                            </Label>
                            <Input
                                id="ch-merchant"
                                value={merchantId}
                                onChange={(e) => setMerchantId(e.target.value)}
                                placeholder="M1234"
                            />
                        </div>
                        <div className="flex flex-col gap-1 w-24">
                            <Label htmlFor="ch-priority">
                                {t("page.billing.channels.field.priority")}
                            </Label>
                            <Input
                                id="ch-priority"
                                type="number"
                                value={priority}
                                onChange={(e) => setPriority(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="flex flex-col gap-1">
                        <Label htmlFor="ch-secret">
                            {t("page.billing.channels.field.secret_key")}
                        </Label>
                        <Input
                            id="ch-secret"
                            type="password"
                            value={secretKey}
                            onChange={(e) => setSecretKey(e.target.value)}
                            placeholder={
                                editing
                                    ? t("page.billing.channels.field.secret_key_rotate_placeholder")
                                    : ""
                            }
                        />
                        {editing && (
                            <p className="text-xs text-muted-foreground">
                                {t("page.billing.channels.field.secret_key_rotate_hint")}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-row gap-2 items-center">
                        <Switch
                            id="ch-enabled"
                            checked={enabled}
                            onCheckedChange={setEnabled}
                        />
                        <Label htmlFor="ch-enabled">
                            {t("page.billing.channels.field.enabled")}
                        </Label>
                        <Badge variant={enabled ? "default" : "secondary"}>
                            {enabled
                                ? t("page.billing.channels.status.on")
                                : t("page.billing.channels.status.off")}
                        </Badge>
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        {t("cancel")}
                    </Button>
                    <Button onClick={onSubmit} disabled={submitDisabled}>
                        {pending
                            ? t("page.billing.channels.dialog.saving")
                            : t("submit")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
