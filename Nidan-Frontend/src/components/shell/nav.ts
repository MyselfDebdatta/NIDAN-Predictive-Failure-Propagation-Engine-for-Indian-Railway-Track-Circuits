import {
  Activity,
  CalendarRange,
  CircuitBoard,
  ClipboardCheck,
  FileSearch,
  ListOrdered,
  Network,
  Palette,
  ShieldCheck,
} from "lucide-react";
import type { StringKey } from "@/i18n/strings";

export type NavTarget =
  | "/"
  | "/alerts"
  | "/assets/$assetId"
  | "/clusters"
  | "/blocks"
  | "/models"
  | "/review"
  | "/field"
  | "/design";

export interface NavItem {
  to: NavTarget;
  label: StringKey;
  short?: StringKey;
  Icon: typeof Activity;
  match: (pathname: string) => boolean;
  count?: "alerts" | "clusters";
}

export const PRIMARY_ASSET = "ADRA/TC/12T";

export const navGroups: { label: StringKey; items: NavItem[] }[] = [
  {
    label: "nav.operate",
    items: [
      {
        to: "/",
        label: "nav.home",
        short: "nav.homeShort",
        Icon: Activity,
        match: (p) => p === "/",
      },
      {
        to: "/alerts",
        label: "nav.alerts",
        short: "nav.alertsShort",
        Icon: ListOrdered,
        match: (p) => p.startsWith("/alerts"),
        count: "alerts",
      },
      {
        to: "/assets/$assetId",
        label: "nav.asset",
        short: "nav.assetShort",
        Icon: CircuitBoard,
        match: (p) => p.startsWith("/assets"),
      },
      {
        to: "/clusters",
        label: "nav.clusters",
        Icon: Network,
        match: (p) => p.startsWith("/clusters"),
        count: "clusters",
      },
      {
        to: "/blocks",
        label: "nav.blocks",
        Icon: CalendarRange,
        match: (p) => p.startsWith("/blocks"),
      },
    ],
  },
  {
    label: "nav.assure",
    items: [
      {
        to: "/models",
        label: "nav.models",
        short: "nav.modelsShort",
        Icon: ShieldCheck,
        match: (p) => p.startsWith("/models"),
      },
      {
        to: "/review",
        label: "nav.review",
        short: "nav.reviewShort",
        Icon: FileSearch,
        match: (p) => p.startsWith("/review"),
      },
      {
        to: "/field",
        label: "nav.field",
        short: "nav.fieldShort",
        Icon: ClipboardCheck,
        match: (p) => p.startsWith("/field"),
      },
    ],
  },
  {
    label: "nav.reference",
    items: [
      { to: "/design", label: "nav.design", Icon: Palette, match: (p) => p.startsWith("/design") },
    ],
  },
];

const all = navGroups.flatMap((g) => g.items);
const pick = (to: NavTarget) => all.find((item) => item.to === to)!;

export const bottomTabs: NavItem[] = [
  pick("/"),
  pick("/alerts"),
  pick("/assets/$assetId"),
  pick("/models"),
  pick("/field"),
];
export const moreItems: NavItem[] = [
  pick("/clusters"),
  pick("/blocks"),
  pick("/review"),
  pick("/design"),
];
