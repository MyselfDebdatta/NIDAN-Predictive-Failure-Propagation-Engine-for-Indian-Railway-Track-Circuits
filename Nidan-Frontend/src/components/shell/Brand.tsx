import { Link } from "@tanstack/react-router";
import { SignalMark } from "@/components/nidan/primitives";
import { cn } from "@/lib/utils";

export function Brand({ className, to = "/" }: { className?: string; to?: "/" | "/field" }) {
  return (
    <Link
      to={to}
      aria-label="NIDAN — home"
      className={cn("flex min-h-11 shrink-0 items-center gap-2.5", className)}
    >
      <span className="grid h-8 w-8 place-items-center rounded-sm border border-border-strong text-accent">
        <SignalMark className="h-5 w-5" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-display text-[17px] font-semibold tracking-[0.06em] text-text-hi">
          NIDAN
        </span>
        <span lang="hi" className="text-[11px] leading-4 text-text-lo">
          निदान
        </span>
      </span>
    </Link>
  );
}
