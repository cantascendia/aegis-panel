/**
 * Nilou design system primitives — barrel export.
 *
 * Source of truth: `docs/design-system-source/project/site/lib/`.
 * Ports `Atoms.jsx` + `PanelShell.jsx` + `PanelPages1.jsx` design
 * primitives to TypeScript with shadcn HSL token integration.
 *
 * Use these for any Nilou-styled operator dashboard route. shadcn
 * `Card` / `Badge` / `Button` from `@marzneshin/common/components/ui`
 * stay available for forms / dialogs / utility layouts.
 */
export { LotusMark } from './LotusMark';
export type { LotusMarkProps } from './LotusMark';

export { StatusDot } from './StatusDot';
export type { StatusDotProps, StatusTone } from './StatusDot';

export { Pill } from './Pill';
export type { PillProps, PillTone } from './Pill';

export { Eyebrow } from './Eyebrow';
export type { EyebrowProps } from './Eyebrow';

export { NilouIcon } from './NilouIcon';
export type { NilouIconProps, NilouIconName } from './NilouIcon';

export { Card as NilouCard, CardHeader as NilouCardHeader } from './Card';
export type { CardProps as NilouCardProps, CardHeaderProps as NilouCardHeaderProps } from './Card';

export { Sparkline } from './Sparkline';
export type { SparklineProps } from './Sparkline';

export { KPI } from './KPI';
export type { KPIProps, KPIAccent } from './KPI';

export { RingMeter } from './RingMeter';
export type { RingMeterProps } from './RingMeter';

export { BigChart } from './BigChart';
export type { BigChartProps } from './BigChart';

export { Row as NilouRow } from './Row';
export type { RowProps as NilouRowProps } from './Row';

export { PanelHead } from './PanelHead';
export type { PanelHeadProps } from './PanelHead';

export { PanelShell } from './PanelShell';
