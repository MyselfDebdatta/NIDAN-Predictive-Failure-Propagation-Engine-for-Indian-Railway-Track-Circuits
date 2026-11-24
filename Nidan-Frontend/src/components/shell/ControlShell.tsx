import { useEffect, useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { MoreHorizontal, Search, ShieldOff, X } from "lucide-react";
import { Brand } from "@/components/shell/Brand";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { LanguageToggle } from "@/components/shell/LanguageToggle";
import { CommandPalette } from "@/components/shell/CommandPalette";
import {
  PRIMARY_ASSET,
  bottomTabs,
  moreItems,
  navGroups,
  type NavItem,
} from "@/components/shell/nav";
import { Chip } from "@/components/nidan/primitives";
import { alertsQuery, clustersQuery } from "@/lib/queries";
import { dataSource } from "@/lib/api";
import { useT } from "@/i18n/strings";
import { useUi } from "@/stores/ui";
import { cn } from "@/lib/utils";

function useCounts() {
  const { data: alerts } = useQuery(alertsQuery);
  const { data: clusters } = useQuery(clustersQuery);
  return {
    alerts: alerts?.length ?? 0,
    clusters: clusters?.filter((c) => c.state === "open").length ?? 0,
  };
}

function NavLink({
  item,
  pathname,
  variant,
}: {
  item: NavItem;
  pathname: string;
  variant: "rail" | "tab" | "sheet";
}) {
  const { t, lang } = useT();
  const counts = useCounts();
  const active = item.match(pathname);
  const count = item.count ? counts[item.count] : 0;
  const label = variant === "tab" && item.short ? t(item.short) : t(item.label);
  const hiLang = lang === "hi" ? "hi" : undefined;
  const linkProps =
    item.to === "/assets/$assetId"
      ? { to: item.to, params: { assetId: PRIMARY_ASSET } }
      : { to: item.to };
  const onNavigate = () => useUi.getState().setMoreOpen(false);

  if (variant === "tab") {
    return (
      <Link
        {...(linkProps as { to: "/" })}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className={cn(
          "relative flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-semibold",
          active ? "text-accent-text" : "text-text-lo",
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "absolute inset-x-3 top-0 h-0.5 rounded-b-full",
            active ? "bg-accent" : "bg-transparent",
          )}
        />
        <span
          className={cn(
            "grid h-7 w-11 place-items-center rounded-full",
            active && "bg-accent-wash",
          )}
        >
          <item.Icon className="h-[18px] w-[18px]" aria-hidden="true" />
        </span>
        <span lang={hiLang} className="max-w-full truncate leading-4">
          {label}
        </span>
        {count > 0 && (
          <span className="absolute right-[calc(50%-24px)] top-1.5 rounded-full bg-bg-raised px-1 font-data text-[10px] text-text-hi ring-1 ring-border-strong">
            {count}
          </span>
        )}
      </Link>
    );
  }

  return (
    <Link
      {...(linkProps as { to: "/" })}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      title={variant === "rail" ? label : undefined}
      className={cn(
        "group relative flex min-h-11 items-center gap-3 rounded-sm px-3 text-sm font-medium transition-colors duration-[var(--dur-1)]",
        variant === "rail" && "justify-center xl:justify-start",
        active ? "bg-bg-active text-text-hi" : "text-text-mid hover:bg-bg-hover hover:text-text-hi",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-y-2 left-0 w-0.5 rounded-r-full",
          active ? "bg-accent" : "bg-transparent",
        )}
      />
      <item.Icon
        className={cn(
          "h-[18px] w-[18px] shrink-0",
          active ? "text-accent-text" : "text-text-lo group-hover:text-text-mid",
        )}
        aria-hidden="true"
      />
      <span
        lang={hiLang}
        className={cn("min-w-0 flex-1 truncate", variant === "rail" && "sr-only xl:not-sr-only")}
      >
        {label}
      </span>
      {count > 0 && (
        <span
          className={cn(
            "font-data text-xs text-text-lo",
            variant === "rail" && "absolute right-1 top-1 text-[10px] xl:static xl:text-xs",
          )}
        >
          {count}
          <span className="sr-only"> open</span>
        </span>
      )}
    </Link>
  );
}

function IstClock() {
  const [now, setNow] = useState<string | null>(null);
  useEffect(() => {
    const fmt = () =>
      new Intl.DateTimeFormat("en-IN", {
        timeZone: "Asia/Kolkata",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(new Date());
    setNow(fmt());
    const id = window.setInterval(() => setNow(fmt()), 30_000);
    return () => window.clearInterval(id);
  }, []);
  return <span className="font-data text-text-mid">{now ?? "--:--"} IST</span>;
}

function SearchButton() {
  const { t } = useT();
  const setOpen = useUi((s) => s.setPaletteOpen);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hidden min-h-10 w-full max-w-[320px] items-center gap-2 rounded-sm border border-border bg-bg-inset px-3 text-sm text-text-lo hover:border-border-strong md:flex"
      >
        <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="flex-1 truncate text-left">{t("search.placeholder")}</span>
        <kbd className="rounded-xs border border-border px-1.5 font-data text-[11px]">Ctrl K</kbd>
      </button>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t("search.open")}
        className="grid min-h-11 min-w-11 place-items-center rounded-sm border border-border text-text-mid md:hidden"
      >
        <Search className="h-[18px] w-[18px]" aria-hidden="true" />
      </button>
    </>
  );
}

function MoreSheet({ pathname }: { pathname: string }) {
  const open = useUi((s) => s.moreOpen);
  const setOpen = useUi((s) => s.setMoreOpen);
  const { t, lang } = useT();
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className={cn(
            "flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-semibold",
            open ? "text-accent-text" : "text-text-lo",
          )}
        >
          <span className="grid h-7 w-11 place-items-center rounded-full">
            <MoreHorizontal className="h-[18px] w-[18px]" aria-hidden="true" />
          </span>
          <span lang={lang === "hi" ? "hi" : undefined} className="leading-4">
            {t("nav.more")}
          </span>
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-text-hi/25 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-50 max-h-[85dvh] overflow-y-auto rounded-t-lg border-t border-border-strong bg-bg-panel p-4 pb-[max(1rem,env(safe-area-inset-bottom))] text-text-hi shadow-float data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom-4">
          <div className="flex items-center justify-between gap-3">
            <Dialog.Title className="text-base font-semibold">{t("nav.more")}</Dialog.Title>
            <Dialog.Close
              className="grid min-h-11 min-w-11 place-items-center rounded-sm border border-border"
              aria-label="Close"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">
            Other destinations, language and the advisory statement.
          </Dialog.Description>
          <nav aria-label="More destinations" className="mt-3 space-y-1">
            {moreItems.map((item) => (
              <NavLink key={item.to} item={item} pathname={pathname} variant="sheet" />
            ))}
          </nav>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle pt-4">
            <span className="text-sm text-text-mid">
              Language / <span lang="hi">भाषा</span>
            </span>
            <LanguageToggle />
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-text-mid">{t("theme.label")}</span>
            <ThemeToggle />
          </div>
          <p className="mt-4 rounded-sm border border-border-subtle bg-bg-raised p-3 text-xs leading-5 text-text-mid">
            <span lang={lang === "hi" ? "hi" : undefined}>{t("safety.statement")}</span>
            <span className="mt-2 block text-text-lo">
              SSE (Sig) · ADRA · {dataSource === "mock" ? "Demo data" : "Live API"} · models twin
              0.3.1 · GNN 0.2.0 · survival 0.2.4 · classifier 0.2.0
            </span>
          </p>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function ControlShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { t, lang } = useT();
  const hiLang = lang === "hi" ? "hi" : undefined;

  return (
    <div className="flex min-h-dvh flex-col bg-bg-app">
      <a
        href="#main"
        className="sr-only z-[60] rounded-sm bg-bg-panel px-3 py-2 text-sm font-semibold text-text-hi focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to content
      </a>
      <header data-shell-chrome className="sticky top-0 z-40 border-b border-border bg-bg-chrome">
        <div className="flex h-14 items-center gap-2 px-3 sm:gap-3 sm:px-4">
          <Brand />
          <nav
            aria-label="Scope"
            className="hidden min-w-0 items-center gap-1.5 border-l border-border pl-3 font-data text-xs text-text-lo lg:flex"
          >
            <span>SER</span>
            <span aria-hidden="true">/</span>
            <span>ADRA</span>
            <span aria-hidden="true">/</span>
            <span className="text-text-hi">ADRA YARD</span>
          </nav>
          <Chip tone="accent" className="hidden min-[420px]:inline-flex">
            <ShieldOff className="h-3.5 w-3.5" aria-hidden="true" />
            <span lang={hiLang} className="hidden sm:inline">
              {t("safety.advisory")}
            </span>
            <span className="sm:hidden">Advisory</span>
          </Chip>
          <div className="ml-auto flex min-w-0 flex-1 items-center justify-end gap-2">
            <SearchButton />
            <LanguageToggle className="hidden lg:inline-flex" />
            <ThemeToggle compact />
            <span className="hidden whitespace-nowrap rounded-sm border border-border px-2 py-1.5 text-xs text-text-mid 2xl:inline">
              SSE (Sig) · ADRA
            </span>
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <nav
          data-shell-chrome
          aria-label="Primary"
          className="scrollbar-thin sticky top-14 hidden h-[calc(100dvh-3.5rem-2.25rem)] w-16 shrink-0 flex-col gap-4 overflow-y-auto border-r border-border bg-bg-chrome px-2 py-4 md:flex xl:w-60 xl:px-3 landscape-phone:flex landscape-phone:h-[calc(100dvh-3.5rem)]"
        >
          {navGroups.map((group) => (
            <div key={group.label} className="space-y-1">
              <p lang={hiLang} className="eyebrow hidden px-3 pb-1 xl:block">
                {t(group.label)}
              </p>
              <span
                aria-hidden="true"
                className="mx-auto block h-px w-8 bg-border first:hidden xl:hidden"
              />
              {group.items.map((item) => (
                <NavLink key={item.to} item={item} pathname={pathname} variant="rail" />
              ))}
            </div>
          ))}
          <p className="mt-auto hidden rounded-sm border border-border-subtle p-3 text-[11px] leading-4 text-text-lo xl:block">
            <span lang={hiLang}>{t("safety.statement")}</span>
          </p>
        </nav>

        <main
          id="main"
          tabIndex={-1}
          className="min-w-0 flex-1 px-4 pb-28 pt-5 outline-none sm:px-6 md:pb-10 lg:px-8 lg:pt-7 landscape-phone:pb-8"
        >
          <div className="mx-auto w-full max-w-[var(--max-content)]">{children}</div>
          <p className="mx-auto mt-8 max-w-[var(--max-content)] text-xs leading-5 text-text-lo md:hidden">
            <span lang={hiLang}>{t("safety.statement")}</span> · Demo data
          </p>
        </main>
      </div>

      <footer
        data-shell-chrome
        className="sticky bottom-0 z-30 hidden h-9 items-center gap-4 overflow-hidden border-t border-border bg-bg-chrome px-4 text-[11px] text-text-lo md:flex landscape-phone:hidden"
      >
        <span className="flex min-w-0 items-center gap-1.5 truncate">
          <ShieldOff className="h-3.5 w-3.5 shrink-0 text-accent-text" aria-hidden="true" />
          <span lang={hiLang} className="truncate">
            {t("safety.statement")}
          </span>
        </span>
        <span className="ml-auto hidden whitespace-nowrap lg:inline">
          SMMS link · read + draft only
        </span>
        <span className="hidden whitespace-nowrap font-data xl:inline">
          twin 0.3.1 · GNN 0.2.0 · survival 0.2.4 · clf 0.2.0
        </span>
        <Chip tone="warning" className="min-h-6 shrink-0 lg:ml-0">
          {dataSource === "mock" ? "Demo data" : "Live API"}
        </Chip>
        <span className="shrink-0">
          <IstClock />
        </span>
      </footer>

      <nav
        data-shell-chrome
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-bg-chrome pb-[env(safe-area-inset-bottom)] md:hidden landscape-phone:hidden"
      >
        {bottomTabs.map((item) => (
          <NavLink key={item.to} item={item} pathname={pathname} variant="tab" />
        ))}
        <MoreSheet pathname={pathname} />
      </nav>

      <CommandPalette />
    </div>
  );
}
