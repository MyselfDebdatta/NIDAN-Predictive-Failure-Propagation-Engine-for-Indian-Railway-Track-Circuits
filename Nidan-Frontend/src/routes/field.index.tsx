import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { fieldTasksQuery } from "@/lib/queries";
import { formatShortDate } from "@/lib/formatters";
import { FieldFooterNote, FieldShell } from "@/components/field/FieldShell";
import { LevelBadge, levelNamesHi } from "@/components/nidan/primitives";
import { useSync } from "@/stores/sync";
import { useT } from "@/i18n/strings";

export const Route = createFileRoute("/field/")({
  head: () => ({
    meta: [
      { title: "Field tasks · offline-first — NIDAN" },
      {
        name: "description",
        content:
          "Field task list for technicians: the next job, its block window and whether it can be done without signal.",
      },
      { property: "og:title", content: "NIDAN field tasks" },
      {
        property: "og:description",
        content: "What is my next job, and can I do it without signal?",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData(fieldTasksQuery),
  component: FieldTaskList,
});

function FieldTaskList() {
  const { data } = useSuspenseQuery(fieldTasksQuery);
  const { t, lang } = useT();
  const lastSync = useSync((s) => s.lastSync);
  const hi = lang === "hi" ? "hi" : undefined;
  return (
    <FieldShell
      back={{ to: "/", label: lang === "hi" ? "कंट्रोल रूम" : "Control room" }}
      title="ESM gang 1 · ADRA"
    >
      <main className="mx-auto w-full max-w-3xl flex-1 space-y-4 px-4 py-5 sm:px-5">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h1 lang={hi} className="font-display text-2xl font-semibold text-text-hi">
            {t("field.tasks")}
          </h1>
          <p className="text-sm text-text-lo">
            <span lang={hi}>{t("field.lastSync")}</span>{" "}
            <span className="font-data">{lastSync}</span>
          </p>
        </div>
        {data.tasks.length === 0 && (
          <p lang={hi} className="rounded-md border-2 border-border bg-bg-panel p-5 text-base">
            {t("field.noTasks")}
          </p>
        )}
        <ol className="space-y-3">
          {data.tasks.map((task, index) => (
            <li key={task.id}>
              <Link
                to="/field/tasks/$taskId"
                params={{ taskId: task.id }}
                className="flex min-h-14 items-center gap-4 rounded-md border-2 border-border bg-bg-panel p-4 hover:border-border-strong"
              >
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full border-2 border-border font-data text-base font-semibold text-text-hi">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-data text-base font-semibold text-text-hi">
                      {task.assetId}
                    </span>
                    <LevelBadge level={task.level} className="min-h-8 text-sm" />
                    {lang === "hi" && (
                      <span lang="hi" className="text-sm text-text-mid">
                        {levelNamesHi[task.level]}
                      </span>
                    )}
                  </span>
                  <span lang={hi} className="mt-1 block text-base text-text-hi">
                    {lang === "hi" ? task.titleHi : task.title}
                  </span>
                  <span className="mt-1 block font-data text-sm text-text-mid">
                    {task.blockId} · {formatShortDate(task.date)} {task.start}–{task.end} ·{" "}
                    {task.route}
                  </span>
                </span>
                <ChevronRight className="h-6 w-6 shrink-0 text-text-lo" aria-hidden="true" />
                <span className="sr-only" lang={hi}>
                  {t("field.open")}
                </span>
              </Link>
            </li>
          ))}
        </ol>
        <p className="text-sm text-text-lo">Tasks are cached on this device for offline use.</p>
      </main>
      <FieldFooterNote />
    </FieldShell>
  );
}
