import { createFileRoute, notFound, useNavigate } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Camera, CheckCircle2, HelpCircle, SearchX } from "lucide-react";
import { toast } from "sonner";
import { fieldTasksQuery } from "@/lib/queries";
import { dataAdapter, type FieldObservation } from "@/lib/api";
import { formatShortDate } from "@/lib/formatters";
import { loadDraft, queueObservation, removeQueued, saveDraft } from "@/lib/outbox";
import { failureModes, type FailureModeCode } from "@/data/fixtures";
import {
  FieldFooterNote,
  FieldShell,
  useDrainOutbox,
  useOutboxCount,
} from "@/components/field/FieldShell";
import { LevelBadge, levelNamesHi } from "@/components/nidan/primitives";
import { Button } from "@/components/ui/button";
import { useSync } from "@/stores/sync";
import { useT, type StringKey } from "@/i18n/strings";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/field/tasks/$taskId")({
  loader: async ({ context, params }) => {
    const data = await context.queryClient.ensureQueryData(fieldTasksQuery);
    const task = data.tasks.find((t) => t.id === params.taskId);
    if (!task) throw notFound();
    return { assetId: task.assetId };
  },
  head: ({ loaderData }) => ({
    meta: [
      {
        title: loaderData
          ? `Field confirmation · ${loaderData.assetId} — NIDAN`
          : "Field task unavailable — NIDAN",
      },
      {
        name: "description",
        content:
          "Record measurements and a finding for one physical claim, offline-first. Written on this device first, synced in the background.",
      },
      { property: "og:title", content: "NIDAN field confirmation" },
      {
        property: "og:description",
        content: "What am I checking, what did I find, and how do I record it without signal?",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  notFoundComponent: () => (
    <div className="field-surface grid min-h-dvh place-items-center p-6 text-lg">
      Task not found on this device.
    </div>
  ),
  component: FieldConfirm,
});

type Finding = FieldObservation["finding"];
type Measurements = FieldObservation["measurements"];
interface Draft {
  measurements: Measurements;
  finding: Finding | null;
  note: string;
  otherMode: FailureModeCode | "";
  photo: string;
}

const measurementFields: { key: keyof Measurements; label: StringKey; unit: string }[] = [
  { key: "relayCurrent", label: "field.relayCurrent", unit: "mA" },
  { key: "ballastConductance", label: "field.ballast", unit: "× dry" },
  { key: "cableInsulation", label: "field.cable", unit: "MΩ" },
  { key: "feedVoltage", label: "field.feed", unit: "V" },
];

function Step({
  n,
  title,
  children,
  id,
}: {
  n: number;
  title: string;
  children: ReactNode;
  id: string;
}) {
  const { lang } = useT();
  return (
    <section
      aria-labelledby={`${id}-title`}
      className="rounded-lg border-2 border-border bg-bg-panel p-4 sm:p-5"
    >
      <h2 id={`${id}-title`} className="flex items-center gap-3 text-lg font-semibold text-text-hi">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent font-data text-base text-on-accent">
          {n}
        </span>
        <span lang={lang === "hi" ? "hi" : undefined}>{title}</span>
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function FieldConfirm() {
  const { taskId } = Route.useParams();
  const { data } = useSuspenseQuery(fieldTasksQuery);
  const task = data.tasks.find((t) => t.id === taskId)!;
  const { t, lang } = useT();
  const hi = lang === "hi" ? "hi" : undefined;
  const navigate = useNavigate();
  const refreshCount = useOutboxCount();
  const drain = useDrainOutbox();
  const { online, lastSync, setLastSync } = useSync();
  const empty: Draft = {
    measurements: {
      relayCurrent: "",
      ballastConductance: "",
      cableInsulation: "",
      feedVoltage: "",
    },
    finding: null,
    note: "",
    otherMode: "",
    photo: "",
  };
  const [draft, setDraft] = useState<Draft>(empty);
  const [error, setError] = useState<string | null>(null);
  const errorRef = useRef<HTMLDivElement | null>(null);
  const draftRef = useRef(draft);
  draftRef.current = draft;

  useEffect(() => {
    void loadDraft<Draft>(taskId).then((saved) => {
      if (saved) setDraft(saved);
    });
  }, [taskId]);

  const persist = () => void saveDraft(taskId, draftRef.current);
  const setMeasurement = (key: keyof Measurements, value: string) =>
    setDraft((d) => ({
      ...d,
      measurements: { ...d.measurements, [key]: value.replace(/[^0-9.]/g, "") },
    }));

  const cable = Number(draft.measurements.cableInsulation);
  const falsifierHit = draft.measurements.cableInsulation !== "" && cable < 0.5;

  const queue = async () => {
    if (!draft.finding) {
      setError(t("field.required"));
      window.setTimeout(() => errorRef.current?.focus(), 0);
      return;
    }
    if (draft.finding === "something-else" && draft.note.trim().length < 3) {
      setError(
        lang === "hi"
          ? "“कुछ और” के लिए बताएँ कि आपने क्या देखा।"
          : "Describe what you saw for “Something else”.",
      );
      window.setTimeout(() => errorRef.current?.focus(), 0);
      return;
    }
    setError(null);
    const observation: FieldObservation = {
      idempotencyKey: crypto.randomUUID(),
      taskId,
      finding: draft.finding,
      measurements: draft.measurements,
      note: draft.otherMode ? `[${draft.otherMode}] ${draft.note}` : draft.note,
      createdAt: new Date().toISOString(),
    };
    // Same code path online and offline: outbox first, then background sync.
    await queueObservation(observation);
    await saveDraft(taskId, empty);
    await refreshCount();
    toast.success(t("field.queuedToast"));
    // Sent from the outbox when there is signal; otherwise it waits for reconnect.
    void drain();
    void navigate({ to: "/field" });
  };

  const findings: {
    value: Finding;
    label: StringKey;
    hint: StringKey;
    Icon: typeof CheckCircle2;
  }[] = [
    {
      value: "confirmed",
      label: "field.confirmed",
      hint: "field.confirmedHint",
      Icon: CheckCircle2,
    },
    { value: "not-found", label: "field.notFound", hint: "field.notFoundHint", Icon: SearchX },
    {
      value: "something-else",
      label: "field.somethingElse",
      hint: "field.somethingElseHint",
      Icon: HelpCircle,
    },
  ];

  return (
    <FieldShell
      back={{ to: "/field", label: t("field.back") }}
      title={`${task.assetId} · ${task.blockId}`}
    >
      <main className="mx-auto w-full max-w-3xl flex-1 space-y-4 px-4 py-5 sm:px-5">
        <section
          aria-labelledby="task-title"
          className="rounded-lg border-2 border-border bg-bg-panel p-4 sm:p-5"
        >
          <div className="flex flex-wrap items-center gap-2">
            <LevelBadge level={task.level} className="min-h-9 text-sm" />
            {lang === "hi" && (
              <span lang="hi" className="text-base text-text-mid">
                {levelNamesHi[task.level]}
              </span>
            )}
            <span className="font-data text-sm text-text-mid">
              {task.lengthM} m · {task.route}
            </span>
          </div>
          <h1
            id="task-title"
            className="mt-3 font-data text-2xl font-semibold leading-8 text-text-hi"
          >
            {task.assetId}
          </h1>
          <p lang={hi} className="mt-1 text-lg text-text-hi">
            {lang === "hi" ? task.titleHi : task.title}
          </p>
          <p className="mt-2 rounded-md bg-bg-inset px-3 py-2 font-data text-base font-semibold text-text-hi">
            <span lang={hi} className="font-sans font-normal text-text-mid">
              {t("field.block")}
            </span>{" "}
            {task.blockId} · {formatShortDate(task.date)} · {task.start}–{task.end}
          </p>
          <dl className="mt-4 space-y-3">
            <div>
              <dt lang={hi} className="text-sm font-semibold text-text-lo">
                {t("field.hypothesis")}
              </dt>
              <dd lang={hi} className="mt-0.5 text-base text-text-hi">
                {lang === "hi" ? task.hypothesisHi : task.hypothesis}
              </dd>
            </div>
            <div className="rounded-md border-2 border-warning bg-warning-wash p-3">
              <dt lang={hi} className="text-sm font-semibold text-warning">
                {t("field.falsifier")}
              </dt>
              <dd lang={hi} className="mt-0.5 text-base text-text-hi">
                {lang === "hi" ? task.falsifierHi : task.falsifier}
              </dd>
            </div>
          </dl>
        </section>

        <Step n={1} id="step-measure" title={t("field.step1")}>
          <div className="grid gap-4 sm:grid-cols-2">
            {measurementFields.map((field) => (
              <div key={field.key}>
                <label
                  htmlFor={`m-${field.key}`}
                  lang={hi}
                  className="text-base font-semibold text-text-hi"
                >
                  {t(field.label)}
                </label>
                <div className="mt-1.5 flex items-stretch overflow-hidden rounded-md border-2 border-border-strong bg-bg-panel focus-within:border-focus-ring">
                  <input
                    id={`m-${field.key}`}
                    inputMode="decimal"
                    autoComplete="off"
                    value={draft.measurements[field.key]}
                    onChange={(e) => setMeasurement(field.key, e.target.value)}
                    onBlur={persist}
                    className="min-h-14 w-full min-w-0 bg-transparent px-3 font-data text-lg text-text-hi outline-none"
                    placeholder="—"
                  />
                  <span className="grid min-w-16 place-items-center border-l-2 border-border bg-bg-inset px-2 font-data text-sm text-text-mid">
                    {field.unit}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setMeasurement(field.key, task.lastReadings[field.key]);
                    window.setTimeout(persist, 0);
                  }}
                  className="mt-1.5 min-h-12 text-sm font-semibold text-accent-text underline underline-offset-4"
                >
                  <span lang={hi}>{t("field.useLast")}</span>:{" "}
                  <span className="font-data">
                    {task.lastReadings[field.key]} {field.unit}
                  </span>
                </button>
              </div>
            ))}
          </div>
          {falsifierHit && (
            <p
              role="status"
              className="mt-4 rounded-md border-2 border-critical bg-critical-wash p-3 text-base text-text-hi"
            >
              Cable insulation below 0.5 MΩ — this points to the joint (F2), not F1. Record it and
              choose “Something else”.
            </p>
          )}
          <label className="mt-4 flex min-h-14 cursor-pointer items-center justify-center gap-3 rounded-md border-2 border-dashed border-border-strong bg-bg-inset px-4 text-base font-semibold text-text-hi">
            <Camera className="h-5 w-5" aria-hidden="true" />
            <span lang={hi}>{draft.photo || t("field.photo")}</span>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={(e) => {
                const name = e.target.files?.[0]?.name ?? "";
                setDraft((d) => ({ ...d, photo: name }));
                window.setTimeout(persist, 0);
              }}
            />
          </label>
        </Step>

        <Step n={2} id="step-finding" title={t("field.step2")}>
          <div role="radiogroup" aria-labelledby="step-finding-title" className="grid gap-3">
            {findings.map(({ value, label, hint, Icon }) => {
              const checked = draft.finding === value;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={checked}
                  onClick={() => {
                    setDraft((d) => ({ ...d, finding: value }));
                    setError(null);
                    window.setTimeout(persist, 0);
                  }}
                  className={cn(
                    "flex min-h-16 items-center gap-4 rounded-md border-2 p-4 text-left",
                    checked
                      ? "border-accent bg-accent-wash"
                      : "border-border bg-bg-panel hover:border-border-strong",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "grid h-7 w-7 shrink-0 place-items-center rounded-full border-2",
                      checked ? "border-accent" : "border-border-strong",
                    )}
                  >
                    {checked && <span className="h-3.5 w-3.5 rounded-full bg-accent" />}
                  </span>
                  <Icon
                    className={cn(
                      "h-6 w-6 shrink-0",
                      checked ? "text-accent-text" : "text-text-lo",
                    )}
                    aria-hidden="true"
                  />
                  <span className="min-w-0">
                    <span lang={hi} className="block text-lg font-semibold text-text-hi">
                      {t(label)}
                    </span>
                    <span lang={hi} className="block text-sm text-text-mid">
                      {t(hint)}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
          {draft.finding && (
            <div className="mt-4 space-y-3">
              {draft.finding === "something-else" && (
                <div>
                  <label htmlFor="other-mode" className="text-base font-semibold text-text-hi">
                    Failure mode, if known
                  </label>
                  <select
                    id="other-mode"
                    value={draft.otherMode}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, otherMode: e.target.value as FailureModeCode | "" }))
                    }
                    onBlur={persist}
                    className="mt-1.5 min-h-14 w-full rounded-md border-2 border-border-strong bg-bg-panel px-3 text-base text-text-hi"
                  >
                    <option value="">Not sure</option>
                    {(Object.keys(failureModes) as FailureModeCode[]).map((code) => (
                      <option key={code} value={code}>
                        {code} · {failureModes[code]}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label htmlFor="note" lang={hi} className="text-base font-semibold text-text-hi">
                  {t("field.note")}
                  {draft.finding === "something-else" ? " *" : ""}
                </label>
                <textarea
                  id="note"
                  rows={3}
                  value={draft.note}
                  onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value }))}
                  onBlur={persist}
                  className="mt-1.5 w-full rounded-md border-2 border-border-strong bg-bg-panel p-3 text-base text-text-hi"
                />
              </div>
            </div>
          )}
        </Step>

        <Step n={3} id="step-confirm" title={t("field.step3")}>
          <p lang={hi} className="text-base text-text-mid">
            {t("field.summary")}
          </p>
          <dl className="mt-3 divide-y-2 divide-border rounded-md border-2 border-border">
            {[
              ["Asset", task.assetId],
              [
                lang === "hi" ? "निष्कर्ष" : "Finding",
                draft.finding ? t(findings.find((f) => f.value === draft.finding)!.label) : "—",
              ],
              ...measurementFields.map(
                (f) =>
                  [
                    t(f.label),
                    draft.measurements[f.key] ? `${draft.measurements[f.key]} ${f.unit}` : "—",
                  ] as [string, string],
              ),
              ["Block", `${task.blockId} · ${task.start}–${task.end}`],
              ["SMMS", lang === "hi" ? "ड्राफ़्ट · समीक्षा बाकी" : "Draft · awaits SSE review"],
            ].map(([label, value]) => (
              <div key={label} className="flex flex-wrap justify-between gap-x-4 gap-y-1 px-3 py-3">
                <dt lang={hi} className="text-sm text-text-lo">
                  {label}
                </dt>
                <dd className="text-base font-semibold text-text-hi">{value}</dd>
              </div>
            ))}
          </dl>
          {error && (
            <div
              ref={errorRef}
              tabIndex={-1}
              role="alert"
              lang={hi}
              className="mt-3 rounded-md border-2 border-critical bg-critical-wash p-3 text-base font-semibold text-critical"
            >
              {error}
            </div>
          )}
        </Step>
        <FieldFooterNote />
      </main>

      <footer className="sticky bottom-0 z-30 border-t-2 border-border bg-bg-chrome pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2 px-3 py-3 sm:gap-3 sm:px-5">
          <p className="w-full text-sm text-text-lo sm:mr-auto sm:w-auto">
            <span lang={hi}>{t("field.lastSync")}</span>{" "}
            <span className="font-data text-text-mid">{lastSync}</span>
            {!online && (
              <span lang={hi} className="ml-1 font-semibold text-warning">
                · {t("field.offline")}
              </span>
            )}
          </p>
          <Button
            size="field"
            variant="outline"
            className="flex-1 border-2 sm:flex-none"
            onClick={() => {
              persist();
              toast(t("field.saved"));
            }}
          >
            <span lang={hi}>{t("field.saveDraft")}</span>
          </Button>
          <Button size="field" className="flex-1 sm:flex-none" onClick={() => void queue()}>
            <span lang={hi}>{t("field.queue")}</span>
          </Button>
        </div>
      </footer>
    </FieldShell>
  );
}
