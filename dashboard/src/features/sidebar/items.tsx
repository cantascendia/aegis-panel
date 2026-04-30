import { SidebarObject } from '@marzneshin/common/components';
import {
    Activity,
    Box,
    CreditCard,
    FileText,
    History,
    Home,
    Landmark,
    ShieldAlert,
    ShieldCheck,
    ShoppingCart,
    Server,
    ServerCog,
    Settings,
    UsersIcon,
} from 'lucide-react';

/**
 * Billing checkout entry — admin-only (per BRIEF-billing-user-auth-blocker
 * option A: A.4 is repurposed as admin-on-behalf-of-user). The
 * non-sudo sidebar deliberately does NOT include this.
 *
 * Replaces the original A.4 flag-gated `userBillingItems` block from
 * PR #41 — once the option-A flip-on landed, the flag is gone, and
 * the entry slots into the existing Billing group with the other
 * admin pages (Plans / Channels / Invoices).
 */

export const sidebarItems: SidebarObject = {
    Dashboard: [
        {
            title: 'Home',
            to: '/',
            icon: <Home />,
            isParent: false,
        },
    ],
    Management: [
        {
            title: 'Users',
            to: '/users',
            icon: <UsersIcon />,
            isParent: false,
        },
        {
            title: 'Services',
            to: '/services',
            icon: <Server />,
            isParent: false,
        },
        {
            title: 'Nodes',
            to: '/nodes',
            icon: <Box />,
            isParent: false,
        },
        {
            title: 'Hosts',
            to: '/hosts',
            icon: <ServerCog />,
            isParent: false,
        },
    ],
    Billing: [
        {
            title: 'Checkout',
            to: '/billing/purchase',
            icon: <ShoppingCart />,
            isParent: false,
        },
        {
            title: 'Plans',
            to: '/billing/plans',
            icon: <CreditCard />,
            isParent: false,
        },
        {
            title: 'Channels',
            to: '/billing/channels',
            icon: <Landmark />,
            isParent: false,
        },
        {
            title: 'Invoices',
            to: '/billing/invoices',
            icon: <FileText />,
            isParent: false,
        },
    ],
    System: [
        {
            title: 'Admins',
            to: '/admins',
            icon: <ShieldCheck />,
            isParent: false,
        },
        {
            title: 'Health',
            to: '/health',
            icon: <Activity />,
            isParent: false,
        },
        {
            title: 'Reality audit',
            to: '/reality',
            icon: <ShieldAlert />,
            isParent: false,
        },
        {
            title: 'Audit log',
            to: '/audit',
            icon: <History />,
            isParent: false,
        },
        {
            title: 'Settings',
            to: '/settings',
            icon: <Settings />,
            isParent: false,
        },
    ],
};

export const sidebarItemsNonSudoAdmin: SidebarObject = {
    Dashboard: [
        {
            title: 'Home',
            to: '/',
            icon: <Home />,
            isParent: false,
        },
    ],
    Management: [
        {
            title: 'Users',
            to: '/users',
            icon: <UsersIcon />,
            isParent: false,
        },
    ],
};
