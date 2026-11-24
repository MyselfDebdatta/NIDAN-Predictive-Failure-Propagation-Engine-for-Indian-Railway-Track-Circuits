import { useCallback, useEffect, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, CloudOff, Wifi } from "lucide-react";
import { LanguageToggle } from "@/components/shell/LanguageToggle";
import { SignalMark } from "@/components/nidan/primitives";
import { useSync } from "@/stores/sync";
import { useT } from "@/i18n/strings";
import { countQueued, drainOutbox } from "@/lib/outbox";
import { dataAdapter } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

/** Demo baseline: three observations from earlier tasks are waiting for signal. */
export const DEMO_QUEUED = 3;

export function useOutboxCount() {
  const setQueued = useSync((s) => s.setQueued);
  return useCallback(async () => setQueued(DEMO_QUEUED + (await countQueued())), [setQueued]);
}

const istNow = () =>
  new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date());

/** Sends the on-device outbox when there is signal; called on load, on reconnect and after each confirmation. */
export function useDrainOutbox() {
  const refresh = useOutboxCount();
  const setLastSync = useSync((s) => s.setLastSync);
  return useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.onLine) return;
    const result = await drainOutbox((observation) => dataAdapter.submitObservation(observation));
    await refresh();
    if (result.sent.length) {
      setLastSync(`${istNow()} IST`);
      const last = result.sent.at(-1);
      toast(
        `Synced ${result.sent.length} ${result.sent.length === 1 ? "observation" : "observations"}${last ? ` · ${last.receipt}` : ""}`,
        { description: "SMMS draft created. Not yet reviewed." },
      );
    }
  }, [refresh, setLastSync]);
}

export function OfflineBadge() {
  const { online, queued } = useSync();
  const { t, lang } = useT();
  const hi = lang === "hi" ? "hi" : undefined;
  return (
    <span
      className="inline-flex min-h-11 items-center gap-2 rounded-md border-2 border-border px-3 text-sm font-semibold text-text-hi"
      role="status"
    >
      <span
        aria-hidden="true"
        className={cn("h-2.5 w-2.5 rounded-full", online ? "bg-ok" : "bg-warning")}
      />
      {online ? (
        <Wifi className="h-4 w-4 max-sm:hidden" aria-hidden="true" />
      ) : (
        <CloudOff className="h-4 w-4 max-sm:hidden" aria-hidden="true" />
      )}
      <span lang={hi} className="max-sm:sr-only">
        {online ? t("field.online") : t("field.offline")} ·
      </span>
      <span>
        <span className="font-data">{queued}</span> <span lang={hi}>{t("field.queued")}</span>
      </span>
    </span>
  );
}

export function FieldShell({
  children,
  back,
  title,
}: {
  children: ReactNode;
  back: { to: "/" | "/field"; label: string };
  title: string;
}) {
  const setOnline = useSync((s) => s.setOnline);
  const refresh = useOutboxCount();
  const drain = useDrainOutbox();
  const { t, lang } = useT();
  useEffect(() => {
    const update = () => {
      setOnline(navigator.onLine);
      if (navigator.onLine) void drain();
    };
    update();
    void refresh();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, [setOnline, refresh, drain]);

  return (
    <div className="field-surface flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b-2 border-border bg-bg-chrome">
        <div className="mx-auto flex min-h-16 max-w-3xl flex-wrap items-center gap-2 px-3 py-2 sm:gap-3 sm:px-5">
          <Link
            to={back.to}
            className="inline-flex min-h-14 min-w-14 items-center justify-center gap-2 rounded-md border-2 border-border px-3 text-base font-semibold text-text-hi"
            aria-label={back.label}
          >
            <ArrowLeft className="h-5 w-5" aria-hidden="true" />
            <span lang={lang === "hi" ? "hi" : undefined} className="max-sm:sr-only">
              {back.label}
            </span>
          </Link>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <SignalMark className="h-6 w-6 shrink-0 text-accent" />
            <span className="min-w-0">
              <span className="block font-display text-sm font-semibold tracking-[0.06em] text-text-hi">
                NIDAN{" "}
                <span className="font-sans font-normal tracking-normal text-text-lo">· Field</span>
              </span>
              <span className="block truncate font-data text-sm font-semibold text-text-hi">
                {title}
              </span>
            </span>
          </div>
          <OfflineBadge />
          <LanguageToggle size="field" />
        </div>
      </header>
      {children}
    </div>
  );
}

export function FieldFooterNote() {
  const { lang } = useT();
  return (
    <div className="mx-auto max-w-3xl space-y-1 px-4 pb-6 pt-2 text-sm leading-6 text-text-lo sm:px-5">
      <p>
        NIDAN is advisory. It has no write path to interlocking, signals, routes or track circuits.
      </p>
      <p lang="hi">
        NIDAN केवल परामर्शी है। इंटरलॉकिंग, सिग्नल, रूट या ट्रैक सर्किट पर इसका कोई नियंत्रण नहीं
        है।
      </p>
      <p>
        {lang === "hi" ? (
          <span lang="hi">
            धूप में पढ़ने के लिए फ़ील्ड ऐप हमेशा उच्च-कंट्रास्ट हल्की सतह का उपयोग करता है।
          </span>
        ) : (
          "The field app always uses a high-contrast light surface for sunlight, whatever your Day/Night choice."
        )}{" "}
        · Demo data
      </p>
    </div>
  );
}
