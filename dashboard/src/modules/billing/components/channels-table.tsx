import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Plus } from "lucide-react";

import {
    Badge,
    Button,
    Loading,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@marzneshin/common/components";

import { useAdminChannels } from "../api";
import type { PaymentChannel } from "../types";
import { ChannelFormDialog } from "./channel-form-dialog";

export const ChannelsTable: FC = () => {
    const { t } = useTranslation();
    const { data: channels, isLoading, isError, error } = useAdminChannels();

    const [dialogOpen, setDialogOpen] = useState(false);
    const [editing, setEditing] = useState<PaymentChannel | null>(null);

    const openCreate = () => {
        setEditing(null);
        setDialogOpen(true);
    };
    const openEdit = (channel: PaymentChannel) => {
        setEditing(channel);
        setDialogOpen(true);
    };

    if (isLoading) return <Loading />;
    if (isError) {
        return (
            <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                {t("page.billing.channels.load_error")}: {(error as Error).message}
            </div>
        );
    }

    const rows = channels ?? [];

    return (
        <div className="flex flex-col gap-3">
            <div className="flex flex-row justify-between items-center">
                <div>
                    <h2 className="text-lg font-semibold">
                        {t("page.billing.channels.title")}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        {t("page.billing.channels.subtitle")}
                    </p>
                </div>
                <Button onClick={openCreate}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t("page.billing.channels.create_button")}
                </Button>
            </div>

            {rows.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-10 border rounded-md">
                    {t("page.billing.channels.empty")}
                </div>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>
                                {t("page.billing.channels.col.code")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.channels.col.name")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.channels.col.merchant_id")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.channels.col.priority")}
                            </TableHead>
                            <TableHead>
                                {t("page.billing.channels.col.enabled")}
                            </TableHead>
                            <TableHead className="w-10" />
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((channel) => (
                            <TableRow key={channel.id}>
                                <TableCell className="font-mono text-sm">
                                    {channel.channel_code}
                                </TableCell>
                                <TableCell>{channel.display_name}</TableCell>
                                <TableCell className="font-mono text-xs">
                                    {channel.merchant_id}
                                </TableCell>
                                <TableCell className="tabular-nums">
                                    {channel.priority}
                                </TableCell>
                                <TableCell>
                                    <Badge
                                        variant={
                                            channel.enabled
                                                ? "default"
                                                : "secondary"
                                        }
                                    >
                                        {channel.enabled
                                            ? t("page.billing.channels.status.on")
                                            : t("page.billing.channels.status.off")}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => openEdit(channel)}
                                    >
                                        <Pencil className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            )}

            <ChannelFormDialog
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                channel={editing}
            />
        </div>
    );
};
