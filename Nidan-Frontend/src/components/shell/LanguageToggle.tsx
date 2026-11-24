import { useUi, type Lang } from "@/stores/ui";
import { cn } from "@/lib/utils";

export function LanguageToggle({
  className,
  size = "control",
}: {
  className?: string;
  size?: "control" | "field";
}) {
  const lang = useUi((state) => state.lang);
  const setLang = useUi((state) => state.setLang);
  const options: { value: Lang; label: string; name: string }[] = [
    { value: "en", label: "EN", name: "English" },
    { value: "hi", label: "हिं", name: "हिन्दी" },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Language / भाषा"
      className={cn(
        "inline-flex shrink-0 rounded-sm border border-border bg-bg-inset p-0.5",
        size === "field" && "border-2",
        className,
      )}
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={lang === option.value}
          aria-label={option.name}
          lang={option.value === "hi" ? "hi" : "en"}
          onClick={() => setLang(option.value)}
          className={cn(
            "inline-flex items-center justify-center rounded-[var(--r-xs)] px-2.5 text-xs font-semibold",
            size === "field" ? "min-h-12 min-w-12 text-base" : "min-h-10 min-w-10",
            lang === option.value
              ? "bg-bg-panel text-text-hi shadow-panel ring-1 ring-border-strong"
              : "text-text-lo hover:text-text-hi",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
