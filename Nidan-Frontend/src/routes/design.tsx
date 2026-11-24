import { createFileRoute } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { alert12T, signalFixtures, alertFixtures } from "@/data/fixtures";
import {
  BlockFitBadge,
  Chip,
  DataTrust,
  KpiTile,
  LevelBadge,
  LevelGlyph,
  Notice,
  PageHeading,
  Panel,
  RiskBar,
  StageRail,
  StateShapeLegend,
  levelNames,
  levelNamesHi,
} from "@/components/nidan/primitives";
import { RulBand, ShapBars, SignalSpine, Sparkline } from "@/components/nidan/charts";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { byPolicyRank } from "@/lib/policy";

export const Route = createFileRoute("/design")({
  head: () => ({
    meta: [
      { title: "Design system reference — NIDAN" },
      {
        name: "description",
        content:
          "Tokens, type, state language, components, data display, motion, accessibility and bilingual vocabulary for NIDAN — rendered from production components.",
      },
      { property: "og:title", content: "NIDAN design system" },
      { property: "og:description", content: "How to build another NIDAN screen correctly." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: DesignSystem,
});

const sections = [
  ["colour", "Colour"],
  ["type", "Type"],
  ["space", "Spacing & grid"],
  ["state", "State language"],
  ["components", "Components"],
  ["data", "Data display"],
  ["motion", "Motion"],
  ["a11y", "Accessibility"],
  ["vocab", "Bilingual vocabulary"],
  ["voice", "Voice"],
] as const;

const colourTokens = [
  ["--bg-app", "App ground"],
  ["--bg-chrome", "Chrome"],
  ["--bg-panel", "Panel"],
  ["--bg-raised", "Raised"],
  ["--bg-inset", "Inset"],
  ["--border", "Border"],
  ["--border-strong", "Border strong"],
  ["--text-hi", "Text high"],
  ["--text-mid", "Text mid"],
  ["--text-lo", "Text low"],
  ["--accent", "Signal teal (graphics)"],
  ["--accent-text", "Teal text"],
  ["--warning", "Warning"],
  ["--critical", "Critical"],
  ["--ok", "OK"],
  ["--focus-ring", "Focus ring"],
] as const;

function Section({
  id,
  n,
  title,
  children,
  note,
}: {
  id: string;
  n: number;
  title: string;
  children: ReactNode;
  note?: string;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-h`}
      className="scroll-mt-24 space-y-4 border-t border-border pt-6"
    >
      <div>
        <p className="eyebrow">{String(n).padStart(2, "0")}</p>
        <h2 id={`${id}-h`} className="mt-1 font-display text-xl font-semibold text-text-hi">
          {title}
        </h2>
        {note && <p className="mt-1 max-w-3xl text-sm text-text-mid">{note}</p>}
      </div>
      {children}
    </section>
  );
}

function DesignSystem() {
  return (
    <div className="space-y-8">
      <PageHeading
        eyebrow="Reference"
        title="Design system"
        titleHi="डिज़ाइन सिस्टम"
        subtitle="Rendered from the same tokens and components the product uses. This is the only page that shows every state side by side, because its job is comparison."
      >
        <ThemeToggle />
      </PageHeading>

      <nav aria-label="Sections" className="flex flex-wrap gap-2">
        {sections.map(([id, label]) => (
          <a
            key={id}
            href={`#${id}`}
            className="inline-flex min-h-11 items-center rounded-sm border border-border px-3 text-sm text-text-mid hover:bg-bg-hover hover:text-text-hi"
          >
            {label}
          </a>
        ))}
      </nav>

      <Section
        id="colour"
        n={1}
        title="Colour"
        note="Two themes, one set of names. Components use semantic variables only — switch Day / Night above to compare. Signal teal on paper is for graphics; small teal text uses the deeper teal token."
      >
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-8">
          {colourTokens.map(([token, label]) => (
            <li key={token} className="min-w-0 overflow-hidden rounded-md border border-border">
              <div
                className="h-14 border-b border-border"
                style={{ background: `var(${token})` }}
              />
              <div className="p-2">
                <p className="truncate text-xs font-semibold text-text-hi">{label}</p>
                <p className="truncate font-data text-[11px] text-text-lo">{token}</p>
              </div>
            </li>
          ))}
        </ul>
        <p className="text-xs text-text-lo">
          The brand never uses red; the product uses red for Critical only. Gold is for caution and
          precedent, never decoration. No gradients on surfaces, no glow.
        </p>
      </Section>

      <Section
        id="type"
        n={2}
        title="Type"
        note="Archivo 600 for display, Inter for UI, JetBrains Mono for IDs and numbers, Noto Sans Devanagari for Hindi. Tabular numerals everywhere."
      >
        <div className="panel-surface space-y-4 p-5">
          <p className="font-display text-[34px] font-semibold leading-[38px] text-text-hi">
            Display 34 · Adra division
          </p>
          <p className="font-display text-[25px] font-semibold leading-[31px] text-text-hi">
            H1 25 · Alert queue
          </p>
          <p className="text-[18px] font-semibold leading-6 text-text-hi">
            H2 18 · Remaining useful life
          </p>
          <p className="text-[14.5px] font-semibold leading-5 text-text-hi">
            H3 14.5 · Likely failure mode
          </p>
          <p className="text-[13.5px] leading-5 text-text-mid">
            Body 13.5 · Effective ballast conductance +31% in 12 days; relay margin 73% of dry.
          </p>
          <p className="text-xs text-text-lo">
            Small 12 · Conformal coverage 0.897 on 3,180 held-out outcomes
          </p>
          <p className="font-data text-sm text-text-hi">
            Mono · ADRA/TC/12T · 24% · 9 d · SMMS-evt-118
          </p>
          <p className="eyebrow">Eyebrow · max four words</p>
          <p lang="hi" className="text-[15px] text-text-hi">
            ट्रैक सर्किट · शेष उपयोगी आयु 9 दिन · बैलास्ट प्रतिरोध
          </p>
        </div>
      </Section>

      <Section
        id="space"
        n={3}
        title="Spacing & grid"
        note="8-point spacing, a 12-column grid with 20 px gutters, small radii (3/5/8/12 px), one soft elevation. Content centres at 1560 px on wall displays."
      >
        <div className="panel-surface space-y-3 p-5">
          {[4, 8, 12, 16, 20, 24, 32, 40, 48].map((s) => (
            <div key={s} className="flex items-center gap-3">
              <span className="w-10 font-data text-xs text-text-lo">{s}</span>
              <span className="h-3 rounded-xs bg-accent" style={{ width: s * 3 }} />
            </div>
          ))}
          <div className="grid grid-cols-12 gap-[20px] pt-2" aria-hidden="true">
            {Array.from({ length: 12 }, (_, i) => (
              <span key={i} className="h-10 rounded-xs bg-accent-wash" />
            ))}
          </div>
        </div>
      </Section>

      <Section
        id="state"
        n={4}
        title="State language"
        note="Four states, four shapes — always shape + word + number. Greyscale stays readable."
      >
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {(["nominal", "watch", "warning", "critical"] as const).map((level) => (
            <div key={level} className="panel-surface space-y-3 p-4">
              <div className="flex items-center gap-2">
                <LevelGlyph level={level} className="h-5 w-5" />
                <span className="text-sm font-semibold text-text-hi">{levelNames[level]}</span>
                <span lang="hi" className="text-sm text-text-mid">
                  {levelNamesHi[level]}
                </span>
              </div>
              <LevelBadge level={level} />
              <p className="text-xs text-text-lo">
                {
                  {
                    nominal: "Solid dot. No action.",
                    watch: "Hollow ring. 7 d risk > 20% or RUL p10 < 30 d, 3 evaluations.",
                    warning:
                      "Filled triangle. 72 h risk > 30% with relay margin in early-warning band.",
                    critical:
                      "Diamond with dark core. 24 h risk > 50% with high confidence, or cluster root cause.",
                  }[level]
                }
              </p>
            </div>
          ))}
        </div>
        <StateShapeLegend />
      </Section>

      <Section
        id="components"
        n={5}
        title="Components"
        note="One primary action per screen. 44 px minimum targets (56 px in the field). No control affordance for interlocking, signals, routes or track circuits exists — not even disabled."
      >
        <div className="panel-surface space-y-5 p-5">
          <div className="flex flex-wrap gap-2">
            <Button>Draft SMMS entry</Button>
            <Button variant="outline">Export pack</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Refresh</Button>
            <Button variant="link">Show as table</Button>
          </div>
          <div className="flex flex-wrap gap-2">
            <Chip tone="accent">Advisory · non-vital</Chip>
            <Chip tone="mono">c-9917</Chip>
            <Chip tone="warning">as of 14:26 IST</Chip>
            <DataTrust score={0.62} flags={["age_vs_signature_mismatch"]} />
            <DataTrust score={0.89} flags={[]} />
          </div>
          <div className="flex flex-wrap gap-2">
            <BlockFitBadge fit="fits" />
            <BlockFitBadge fit="extends" />
            <BlockFitBadge fit="special" />
            <BlockFitBadge fit="none" />
          </div>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiTile label="Open alerts" value="11" delta="+2" note="In scope" />
            <KpiTile
              label="Critical"
              value="1"
              delta="21 min"
              note="Special block"
              tone="critical"
              glyph="critical"
            />
          </div>
          <Notice title="Falsifier">
            If insulation falls below 0.5 MΩ the ranking moves to F2 (joint), not F1.
          </Notice>
          <StageRail
            current="samprapti"
            targets={{
              purvarupa: "state",
              nidana: "components",
              samprapti: "data",
              upasaya: "voice",
            }}
          />
        </div>
      </Section>

      <Section
        id="data"
        n={6}
        title="Data display"
        note="Hand-authored SVG. No donuts, gauges, pulsing rows, heat maps or sparklines without a baseline."
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Signal Spine" eyebrow="Live markup">
            <SignalSpine alerts={byPolicyRank(alertFixtures).slice(0, 4)} />
          </Panel>
          <Panel title="RUL band" eyebrow="Always p10 / median / p90">
            <RulBand alert={alert12T} />
          </Panel>
          <Panel title="Sparkline with baseline" eyebrow="Dashed = dry baseline">
            <div className="grid gap-3 sm:grid-cols-2">
              {signalFixtures.slice(0, 2).map((s) => (
                <Sparkline key={s.key} series={s} />
              ))}
            </div>
          </Panel>
          <Panel title="Signed SHAP" eyebrow="Direction in words">
            <ShapBars features={alert12T.explanation.model.shapTop} />
          </Panel>
          <Panel title="Risk meter" eyebrow="Supplementary bar, never alone">
            <div className="space-y-2">
              {(
                [
                  [0.04, "nominal"],
                  [0.24, "watch"],
                  [0.34, "warning"],
                  [0.52, "critical"],
                ] as const
              ).map(([v, level]) => (
                <div key={v} className="flex items-center gap-3">
                  <LevelGlyph level={level} />
                  <span className="w-10 font-data text-sm text-text-hi">
                    {Math.round(v * 100)}%
                  </span>
                  <RiskBar value={v} level={level} className="w-32" />
                  <span className="text-xs text-text-lo">{levelNames[level]}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </Section>

      <Section
        id="motion"
        n={7}
        title="Motion"
        note="90 / 140 / 200 ms, opacity and ≤ 4 px translate only, ease-out. Drawer slides 12 px. Nothing loops or pulses. Reduced motion collapses all durations."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            ["--dur-1", "90 ms", "Hover, row background"],
            ["--dur-2", "140 ms", "Tabs, toggles"],
            ["--dur-3", "200 ms", "Panels, drawer"],
          ].map(([t, v, use]) => (
            <div key={t} className="panel-surface p-4">
              <p className="font-data text-sm text-text-hi">
                {t} · {v}
              </p>
              <p className="mt-1 text-xs text-text-lo">{use}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="a11y"
        n={8}
        title="Accessibility"
        note="WCAG 2.2 AA in both themes, with stricter internal rules."
      >
        <ul className="grid gap-2 text-sm text-text-mid sm:grid-cols-2">
          {[
            "Real tables with th scope; cards below 720 px keep the same accessible names",
            "Visible 2 px focus ring with 1 px offset",
            "Charts are role=img with sentence summaries and a table equivalent",
            "Keyboard: / search · ↑↓ rows · Enter open · Space select · Shift+Space range · Esc close · Ctrl/⌘ K palette",
            "200% zoom and 400% reflow without horizontal scroll",
            'Hindi spans carry lang="hi"; no truncation or tracking on Devanagari',
          ].map((t) => (
            <li key={t} className="rounded-sm border border-border-subtle p-3">
              {t}
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="vocab"
        n={9}
        title="Bilingual vocabulary"
        note="Field tasks, confirmations, errors, safety copy and navigation are bilingual. Model metrics, SHAP labels and identifiers stay English."
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-text-lo">
                <th scope="col" className="py-2 font-medium">
                  English
                </th>
                <th scope="col" className="py-2 font-medium">
                  हिन्दी
                </th>
                <th scope="col" className="py-2 font-medium">
                  Not
                </th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Track circuit", "ट्रैक सर्किट", "sensor, loop"],
                ["Relay room", "रिले कक्ष", "server room"],
                ["Block / Rolling Block", "ब्लॉक", "outage"],
                ["Failure mode F1–F12", "विफलता प्रकार", "error type"],
                ["Watch / Warning / Critical", "निगरानी / चेतावनी / गंभीर", "low / medium / high"],
                ["Remaining useful life", "शेष उपयोगी आयु", "health score"],
                ["Ballast resistance", "बैलास्ट प्रतिरोध", "—"],
                ["Acknowledge", "स्वीकार करें", "approve, resolve"],
              ].map(([en, hi, not]) => (
                <tr key={en} className="border-b border-border-subtle">
                  <td className="py-2 text-text-hi">{en}</td>
                  <td lang="hi" className="py-2 text-text-hi">
                    {hi}
                  </td>
                  <td className="py-2 text-text-lo">{not}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        id="voice"
        n={10}
        title="Voice"
        note="Calm, specific, physical. Say what the data shows and what would prove it wrong."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="panel-surface p-4">
            <p className="eyebrow text-ok">Do</p>
            <ul className="mt-2 space-y-2 text-sm text-text-hi">
              <li>“Ballast conductance +31% in 12 days; RB-28 can absorb the fix.”</li>
              <li>“Acknowledged · still open.”</li>
              <li>“Predicted, not observed.”</li>
            </ul>
          </div>
          <div className="panel-surface p-4">
            <p className="eyebrow text-critical">Don't</p>
            <ul className="mt-2 space-y-2 text-sm text-text-hi">
              <li>“AI detected an anomaly!”</li>
              <li>“Health score 62/100.”</li>
              <li>“Resolve all” · “Apply to interlocking”.</li>
            </ul>
          </div>
        </div>
      </Section>
    </div>
  );
}
