import { SidebarObject, SidebarItem } from '@marzneshin/common/components';
import {
    Box,
    CreditCard,
    FileText,
    Home,
    Landmark,
    Receipt,
    ShieldCheck,
    ShoppingCart,
    Server,
    ServerCog,
    Settings,
    UsersIcon,
} from 'lucide-react';

/**
 * A.4 user purchase UI is flag-gated OFF by default. When the flag
 * is on, users (sudo AND non-sudo) see "Purchase" and "My invoices"
 * entries under a new "Account" group. Flip-on requires A.2.2 +
 * A.3.1 backend endpoints on main — see
 * docs/ai-cto/WIP-billing-split.md "Flip-on checklist".
 */
const userBillingEnabled =
    import.meta.env.VITE_BILLING_USER_UI === 'on' ||
    import.meta.env.VITE_BILLING_USER_UI === 'true' ||
    import.meta.env.VITE_BILLING_USER_UI === '1';

const userBillingItems: SidebarItem[] = userBillingEnabled
    ? [
          {
              title: 'Purchase',
              to: '/billing/purchase',
              icon: <ShoppingCart />,
              isParent: false,
          },
          {
              title: 'My invoices',
              to: '/billing/my-invoices',
              icon: <Receipt />,
              isParent: false,
          },
      ]
    : [];

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
            title: 'Settings',
            to: '/settings',
            icon: <Settings />,
            isParent: false,
        },
    ],
    ...(userBillingItems.length > 0 ? { Account: userBillingItems } : {}),
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
    ...(userBillingItems.length > 0 ? { Account: userBillingItems } : {}),
};
