import { Moon, Sun } from "lucide-react";
import { applyTheme, useTheme, type NidanTheme } from "@/lib/theme";
import { useT } from "@/i18n/strings";
import { cn } from "@/lib/utils";

/** Explicit Day / Night choice with icon + word. Switching only flips data-theme, so routes, filters and drawers stay mounted. */
export function ThemeToggle({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
  const theme = useTheme();
  const { t, lang } = useT();
  const options: { value: NidanTheme; label: string; Icon: typeof Sun }[] = [
    { value: "day", label: t("theme.day"), Icon: Sun },
    { value: "night", label: t("theme.night"), Icon: Moon },
  ];
  return (
    <div
      role="radiogroup"
      aria-label={t("theme.label")}
      className={cn(
        "inline-flex shrink-0 rounded-sm border border-border bg-bg-inset p-0.5",
        className,
      )}
    >
      {options.map(({ value, label, Icon }) => {
        const active = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            onClick={() => applyTheme(value)}
            className={cn(
              "inline-flex min-h-10 min-w-10 items-center justify-center gap-1.5 rounded-[var(--r-xs)] px-2 text-xs font-semibold transition-colors duration-[var(--dur-2)]",
              active
                ? "bg-bg-panel text-text-hi shadow-panel ring-1 ring-border-strong"
                : "text-text-lo hover:text-text-hi",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            <span
              lang={lang === "hi" ? "hi" : undefined}
              className={cn(compact ? "sr-only min-[400px]:not-sr-only" : "")}
            >
              {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
