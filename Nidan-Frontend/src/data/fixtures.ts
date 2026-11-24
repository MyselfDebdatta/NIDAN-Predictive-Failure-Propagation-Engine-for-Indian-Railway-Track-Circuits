/**
 * NIDAN demo scenario. Every screen reads these fixtures through the data adapter,
 * so assets, timestamps and numbers stay identical across the app. Demo data only —
 * never presented as live readings.
 *
 * Integrity rules enforced by `src/test/fixtures.test.ts`:
 *  - every alert owns its explanation; there is no shared fallback;
 *  - cluster membership is derived from `Alert.clusterId`, never stored twice;
 *  - alert levels satisfy the policy thresholds in the specification;
 *  - the field task's "last reading" equals the last point of the signal series.
 */
export type AlertLevel = "watch" | "warning" | "critical";
export type StateLevel = AlertLevel | "nominal";
export type FailureModeCode =
  "F1" | "F2" | "F3" | "F4" | "F5" | "F6" | "F7" | "F8" | "F9" | "F10" | "F11" | "F12";
export type BlockFit = "fits" | "extends" | "special" | "none";

export const failureModes: Record<FailureModeCode, string> = {
  F1: "Low ballast resistance",
  F2: "Insulated / glued joint",
  F3: "Rail bond / continuity / break",
  F4: "Metallic bridging at points",
  F5: "Relay ageing",
  F6: "Power supply / feed",
  F7: "Lightning / surge",
  F8: "Cable fault",
  F9: "Shunting failure (wrong-side risk)",
  F10: "Stray / traction interference",
  F11: "Maintenance / config error",
  F12: "No-fault-found",
};

export interface BlockWindow {
  id: string;
  date: string;
  start: string;
  end: string;
  durationMin: number;
  kind: "published" | "draft";
}

export interface Explanation {
  physics: {
    headline: string;
    state: { label: string; value: string; baseline: string }[];
    falsifier: string;
  };
  model: {
    shapTop: { feature: string; label: string; value: number }[];
    calibrationNote: string;
    modeSet: FailureModeCode[];
    modeSetCoverage: number;
    agreement: string;
  };
  precedents: {
    smmsId: string;
    assetId: string;
    confirmedMode: FailureModeCode;
    similarity: number;
    daysAgo: number;
    outcome: string;
  }[];
}

/** Ranking inputs are produced by the server policy; the browser only renders them. */
export interface RankingInputs {
  calibratedRisk: number;
  consequence: "high" | "medium" | "low";
  consequenceNote: string;
  exposure: string;
  trustDiscount: number;
  tieBreaker: string;
}

export interface Alert {
  id: string;
  assetId: string;
  assetName: string;
  route: string;
  division: string;
  level: AlertLevel;
  policyRank: number;
  persistence: number;
  risk: { h24: number; h72: number; h7d: number; eceZone: number };
  rul: { p10Days: number; medianDays: number; p90Days: number; coverage: number; heldOutN: number };
  likelyModes: FailureModeCode[];
  modeProbability: number;
  modeSetCoverage: number;
  clusterId?: string;
  dataTrust: { score: number; flags: string[] };
  block?: { window: BlockWindow; fit: BlockFit; minutes: number };
  explanation: Explanation;
  ranking: RankingInputs;
  ageMinutes: number;
  modelVersions: { twin: string; gnn: string; survival: string; classifier: string };
  acknowledged?: boolean;
  deferral?: { reason: string; reviewDate: string };
}

/** Snapshot time for the demo scenario (IST). All "days from now" values derive from this. */
export const snapshot = {
  date: "2026-07-14",
  time: "00:20",
  label: "14 Jul 2026 · 00:20 IST",
  week: 29,
};

export const blockFixtures: BlockWindow[] = [
  {
    id: "RB-26",
    date: "2026-07-14",
    start: "01:40",
    end: "03:10",
    durationMin: 90,
    kind: "published",
  },
  {
    id: "RB-27",
    date: "2026-07-15",
    start: "02:00",
    end: "03:30",
    durationMin: 90,
    kind: "published",
  },
  {
    id: "RB-28",
    date: "2026-07-16",
    start: "02:10",
    end: "03:40",
    durationMin: 90,
    kind: "published",
  },
  {
    id: "RB-29",
    date: "2026-07-17",
    start: "01:50",
    end: "03:20",
    durationMin: 90,
    kind: "published",
  },
  {
    id: "RB-30",
    date: "2026-07-18",
    start: "02:00",
    end: "03:30",
    durationMin: 90,
    kind: "published",
  },
  {
    id: "RB-31",
    date: "2026-07-19",
    start: "00:40",
    end: "02:10",
    durationMin: 90,
    kind: "published",
  },
  {
    id: "RB-32",
    date: "2026-07-20",
    start: "01:30",
    end: "03:00",
    durationMin: 90,
    kind: "published",
  },
];

const win = (id: string): BlockWindow => {
  const found = blockFixtures.find((item) => item.id === id);
  if (!found) throw new Error(`Unknown block ${id}`);
  return found;
};

const modelVersions = { twin: "0.3.1", gnn: "0.2.0", survival: "0.2.4", classifier: "0.2.0" };

const rul = (p10Days: number, medianDays: number, p90Days: number) => ({
  p10Days,
  medianDays,
  p90Days,
  coverage: 0.897,
  heldOutN: 3180,
});

/* ------------------------------------------------------------------ Explanations
 * One explanation per alert. Numbers agree with the alert's risk, mode, trust flag
 * and the field task's last reading where the two describe the same circuit.
 */

const explanation07T: Explanation = {
  physics: {
    headline: "Track relay stays picked for 1.8 s after axle entry on 4 of the last 9 movements",
    state: [
      { label: "Drop-away delay", value: "1.8 s", baseline: "< 0.5 s" },
      { label: "Rail surface", value: "Rusted, low traffic", baseline: "Polished" },
      { label: "Shunt sensitivity", value: "0.31 Ω", baseline: "0.5 Ω design" },
    ],
    falsifier:
      "If drop-away is under 0.5 s on the next five movements, the pattern is a logger timing artefact, not F9.",
  },
  model: {
    shapTop: [
      { feature: "drop_delay_p95", label: "Drop-away delay, p95", value: 0.92 },
      { feature: "traffic_density_7d", label: "Traffic density, 7 d", value: 0.34 },
      { feature: "rail_surface_index", label: "Rail surface condition", value: 0.11 },
    ],
    calibrationNote:
      "Critical band is deliberately conservative: observed 0.47 against predicted 0.52.",
    modeSet: ["F9"],
    modeSetCoverage: 0.9,
    agreement: "high",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-091",
      assetId: "TATA/TC/03T",
      confirmedMode: "F9",
      similarity: 0.79,
      daysAgo: 302,
      outcome: "Rail head cleaned; shunt verified with 0.5 Ω test",
    },
  ],
};

const explanation12T: Explanation = {
  physics: {
    headline: "Effective ballast conductance +31% in 12 days; relay margin 73% of dry",
    state: [
      { label: "Relay current", value: "118 mA", baseline: "162 mA dry" },
      { label: "Ballast conductance", value: "1.31 × dry", baseline: "1.00" },
      { label: "Rain, 72 h", value: "96 mm", baseline: "median 22 mm" },
    ],
    falsifier: "If insulation falls below 0.5 MΩ the ranking moves to F2 (joint), not F1.",
  },
  model: {
    shapTop: [
      { feature: "relay_i_slope_7d", label: "Relay current slope, 7 d", value: -0.41 },
      { feature: "rain_72h", label: "Rainfall, 72 h", value: -0.12 },
      { feature: "ballast_g_ratio", label: "Ballast conductance ratio", value: -0.09 },
      { feature: "feed_v_stability", label: "Feed voltage stability", value: 0.05 },
    ],
    calibrationNote: "Scores in this bin historically over-predict by 2 points; ECE 0.031.",
    modeSet: ["F1", "F4"],
    modeSetCoverage: 0.9,
    agreement: "high",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-118",
      assetId: "ADRA/TC/14T",
      confirmedMode: "F1",
      similarity: 0.88,
      daysAgo: 64,
      outcome: "Drain rodded; 41 days to next alert",
    },
    {
      smmsId: "SMMS-evt-204",
      assetId: "ADRA/TC/09T",
      confirmedMode: "F1",
      similarity: 0.81,
      daysAgo: 148,
      outcome: "Ballast cleared; no recurrence in 10 months",
    },
    {
      smmsId: "SMMS-evt-377",
      assetId: "BKSC/TC/22T",
      confirmedMode: "F4",
      similarity: 0.72,
      daysAgo: 211,
      outcome: "Points bridging; joint replaced",
    },
  ],
};

const explanation14T: Explanation = {
  physics: {
    headline: "Ballast conductance 1.27 × dry after 96 mm rain; relay margin 81% of dry",
    state: [
      { label: "Relay current", value: "131 mA", baseline: "162 mA dry" },
      { label: "Ballast conductance", value: "1.27 × dry", baseline: "1.00" },
      { label: "Cess drain", value: "Silted at chainage 4", baseline: "Running clear" },
    ],
    falsifier:
      "If the cess drain runs clear and conductance stays above 1.2 × dry for 48 h, the cause is the formation, not the drain.",
  },
  model: {
    shapTop: [
      { feature: "ballast_g_ratio", label: "Ballast conductance ratio", value: 0.38 },
      { feature: "rain_72h", label: "Rainfall, 72 h", value: 0.21 },
      { feature: "relay_i_slope_7d", label: "Relay current slope, 7 d", value: 0.14 },
      { feature: "drain_flow", label: "Cess drain flow", value: 0.06 },
    ],
    calibrationNote: "Warning band over-predicts by 3 points in wet months; ECE 0.041.",
    modeSet: ["F1", "F2"],
    modeSetCoverage: 0.88,
    agreement: "high",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-118",
      assetId: "ADRA/TC/14T",
      confirmedMode: "F1",
      similarity: 0.94,
      daysAgo: 64,
      outcome: "Drain rodded; 41 days to next alert",
    },
    {
      smmsId: "SMMS-evt-204",
      assetId: "ADRA/TC/09T",
      confirmedMode: "F1",
      similarity: 0.79,
      daysAgo: 148,
      outcome: "Ballast cleared; no recurrence in 10 months",
    },
    {
      smmsId: "SMMS-evt-902",
      assetId: "ADRA/TC/14T",
      confirmedMode: "F1",
      similarity: 0.71,
      daysAgo: 310,
      outcome: "Cess regraded; no recurrence until June",
    },
  ],
};

const explanation22T: Explanation = {
  physics: {
    headline: "Intermittent occupancy at the points throat on 3 of the last 12 clear movements",
    state: [
      { label: "Gap resistance", value: "0.4 Ω", baseline: "> 2 Ω clear" },
      { label: "Stretcher bar", value: "Metal filings", baseline: "Clean" },
      { label: "Ballast conductance", value: "1.06 × dry", baseline: "1.00" },
    ],
    falsifier:
      "If the gap reads above 2 Ω with the points normal and no debris is present, the cause is the relay, not bridging (F5).",
  },
  model: {
    shapTop: [
      { feature: "points_bridge_events", label: "Points bridging events, 7 d", value: 0.44 },
      { feature: "ballast_g_ratio", label: "Ballast conductance ratio", value: 0.12 },
      { feature: "traffic_density_7d", label: "Traffic density, 7 d", value: 0.09 },
    ],
    calibrationNote:
      "Points-zone alerts under-predict by 2 points above 30 movements a day; ECE 0.044.",
    modeSet: ["F4", "F5"],
    modeSetCoverage: 0.86,
    agreement: "medium",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-377",
      assetId: "BKSC/TC/22T",
      confirmedMode: "F4",
      similarity: 0.91,
      daysAgo: 211,
      outcome: "Points bridging; joint replaced",
    },
    {
      smmsId: "SMMS-evt-845",
      assetId: "ADRA/TC/16T",
      confirmedMode: "F4",
      similarity: 0.74,
      daysAgo: 96,
      outcome: "Debris cleared; stretcher bar adjusted",
    },
  ],
};

const explanation16T: Explanation = {
  physics: {
    headline: "Metal debris at the loop points; shunt margin down to 0.42 Ω on two of nine tests",
    state: [
      { label: "Gap resistance", value: "0.42 Ω", baseline: "> 2 Ω clear" },
      { label: "Stretcher bar", value: "Filings found", baseline: "Clean" },
      { label: "Ballast conductance", value: "1.08 × dry", baseline: "1.00" },
    ],
    falsifier:
      "If the gap reads above 2 Ω after cleaning on the next three tests, re-rank toward F1 (wet ballast), not F4.",
  },
  model: {
    shapTop: [
      { feature: "points_bridge_events", label: "Points bridging events, 7 d", value: 0.31 },
      { feature: "ballast_g_ratio", label: "Ballast conductance ratio", value: 0.18 },
      { feature: "rain_72h", label: "Rainfall, 72 h", value: 0.11 },
    ],
    calibrationNote:
      "Watch band is well calibrated at this score: observed 0.26 against predicted 0.27. ECE 0.033.",
    modeSet: ["F4", "F1"],
    modeSetCoverage: 0.9,
    agreement: "medium",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-845",
      assetId: "ADRA/TC/16T",
      confirmedMode: "F4",
      similarity: 0.88,
      daysAgo: 96,
      outcome: "Debris cleared; stretcher bar adjusted",
    },
    {
      smmsId: "SMMS-evt-377",
      assetId: "BKSC/TC/22T",
      confirmedMode: "F4",
      similarity: 0.72,
      daysAgo: 211,
      outcome: "Points bridging; joint replaced",
    },
  ],
};

const explanation21T: Explanation = {
  physics: {
    headline: "Early ballast signature: conductance 1.08 × dry, relay margin 92% of dry",
    state: [
      { label: "Relay current", value: "149 mA", baseline: "162 mA dry" },
      { label: "Ballast conductance", value: "1.08 × dry", baseline: "1.00" },
      { label: "Cable insulation", value: "0.9 MΩ", baseline: "> 1.0 MΩ" },
    ],
    falsifier:
      "If conductance stays below 1.1 × dry for 14 days while insulation falls below 0.8 MΩ, the cause is the cable route (F8), not drainage.",
  },
  model: {
    shapTop: [
      { feature: "ballast_g_ratio", label: "Ballast conductance ratio", value: 0.22 },
      { feature: "cable_ir_slope_7d", label: "Cable insulation slope, 7 d", value: 0.19 },
      { feature: "rain_72h", label: "Rainfall, 72 h", value: 0.08 },
    ],
    calibrationNote:
      "Cascade members are scored conservatively: observed 0.19 against predicted 0.22. ECE 0.036.",
    modeSet: ["F1", "F8"],
    modeSetCoverage: 0.87,
    agreement: "low",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-204",
      assetId: "ADRA/TC/09T",
      confirmedMode: "F1",
      similarity: 0.76,
      daysAgo: 148,
      outcome: "Ballast cleared; no recurrence in 10 months",
    },
    {
      smmsId: "SMMS-evt-731",
      assetId: "ADRA/TC/18T",
      confirmedMode: "F8",
      similarity: 0.69,
      daysAgo: 34,
      outcome: "Insulation drift on the S3 branch; megger booked",
    },
  ],
};

const explanation05T: Explanation = {
  physics: {
    headline: "Relay pick-up current up 9% in 30 days; drop-away still inside specification",
    state: [
      { label: "Pick-up current", value: "1.09 × commissioning", baseline: "< 1.05 ×" },
      { label: "Drop-away", value: "0.42 s", baseline: "< 0.5 s" },
      { label: "Operations", value: "184k", baseline: "design 200k" },
    ],
    falsifier:
      "If drop-away exceeds 0.5 s on the next test, the relay is out of specification and the level rises to Warning.",
  },
  model: {
    shapTop: [
      { feature: "relay_pickup_slope", label: "Pick-up current slope, 30 d", value: 0.28 },
      { feature: "relay_ops_count", label: "Operating count since renewal", value: 0.15 },
      { feature: "ambient_temp", label: "Relay room temperature", value: 0.05 },
    ],
    calibrationNote:
      "Relay-ageing scores are conservative by design: observed 0.21 against predicted 0.25. ECE 0.029.",
    modeSet: ["F5"],
    modeSetCoverage: 0.91,
    agreement: "high",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-412",
      assetId: "ADRA/TC/05T",
      confirmedMode: "F5",
      similarity: 0.9,
      daysAgo: 188,
      outcome: "Relay replaced; no recurrence",
    },
    {
      smmsId: "SMMS-evt-455",
      assetId: "BKSC/TC/22T",
      confirmedMode: "F5",
      similarity: 0.66,
      daysAgo: 265,
      outcome: "Relay swapped in a 40-minute block",
    },
  ],
};

const explanation09T: Explanation = {
  physics: {
    headline: "Ballast conductance 1.06 × dry; the same signature as the March event, but slower",
    state: [
      { label: "Relay current", value: "152 mA", baseline: "162 mA dry" },
      { label: "Ballast conductance", value: "1.06 × dry", baseline: "1.00" },
      { label: "Cess drain", value: "Running clear", baseline: "Running clear" },
    ],
    falsifier:
      "If conductance rises above 1.15 × dry before the next rain event, the drain has re-silted and the ranking moves to Warning.",
  },
  model: {
    shapTop: [
      { feature: "ballast_g_ratio", label: "Ballast conductance ratio", value: 0.19 },
      { feature: "rain_72h", label: "Rainfall, 72 h", value: 0.07 },
      { feature: "drain_silt", label: "Drain silt index", value: 0.04 },
    ],
    calibrationNote:
      "Assets with a repair in the last 12 months are down-weighted: observed 0.18 against predicted 0.21. ECE 0.034.",
    modeSet: ["F1"],
    modeSetCoverage: 0.9,
    agreement: "high",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-204",
      assetId: "ADRA/TC/09T",
      confirmedMode: "F1",
      similarity: 0.93,
      daysAgo: 148,
      outcome: "Ballast cleared; no recurrence in 10 months",
    },
  ],
};

const explanation31T: Explanation = {
  physics: {
    headline: "Feed voltage dips to 5.7 V on 3 of the last 12 nights; no relay symptom yet",
    state: [
      { label: "Feed voltage, minimum", value: "5.7 V", baseline: "6.0–6.8 V" },
      { label: "Dip duration", value: "1.4 s", baseline: "< 0.5 s" },
      { label: "Relay current", value: "158 mA", baseline: "150–175 mA" },
    ],
    falsifier:
      "If the dips disappear when the standby supply is swapped in, the cause is the charger, not the feeder.",
  },
  model: {
    shapTop: [
      { feature: "feed_v_min", label: "Feed voltage minimum, 7 d", value: 0.26 },
      { feature: "dip_events_7d", label: "Voltage dip events, 7 d", value: 0.14 },
      { feature: "ambient_temp", label: "Relay room temperature", value: 0.03 },
    ],
    calibrationNote:
      "This asset's logger has a 6-hour gap, so the score is discounted and shown as low trust, never suppressed. ECE 0.052.",
    modeSet: ["F6", "F7"],
    modeSetCoverage: 0.84,
    agreement: "low",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-508",
      assetId: "KGP/TC/31T",
      confirmedMode: "F6",
      similarity: 0.81,
      daysAgo: 240,
      outcome: "Charger card replaced",
    },
    {
      smmsId: "SMMS-evt-733",
      assetId: "KGP/TC/29T",
      confirmedMode: "F6",
      similarity: 0.63,
      daysAgo: 320,
      outcome: "Feeder fuse carrier cleaned",
    },
  ],
};

const explanation08T: Explanation = {
  physics: {
    headline:
      "Cable insulation down to 0.72 MΩ on the yard branch; still above the 0.5 MΩ falsifier",
    state: [
      { label: "Cable insulation", value: "0.72 MΩ", baseline: "> 1.0 MΩ" },
      { label: "Relay current", value: "156 mA", baseline: "150–175 mA" },
      { label: "Feed voltage", value: "6.3 V", baseline: "6.0–6.8 V" },
    ],
    falsifier:
      "If insulation falls below 0.5 MΩ, the ranking moves to F2 (joint) and the block moves to this week.",
  },
  model: {
    shapTop: [
      { feature: "cable_ir_slope_7d", label: "Cable insulation slope, 7 d", value: 0.24 },
      { feature: "cable_age", label: "Cable age", value: 0.11 },
      { feature: "rain_72h", label: "Rainfall, 72 h", value: 0.06 },
    ],
    calibrationNote:
      "Cable-fault scores are bimodal; the Watch band is deliberately wide. ECE 0.048.",
    modeSet: ["F8", "F2"],
    modeSetCoverage: 0.86,
    agreement: "medium",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-623",
      assetId: "TATA/TC/08T",
      confirmedMode: "F8",
      similarity: 0.84,
      daysAgo: 402,
      outcome: "Cable tail replaced",
    },
    {
      smmsId: "SMMS-evt-731",
      assetId: "ADRA/TC/18T",
      confirmedMode: "F8",
      similarity: 0.61,
      daysAgo: 34,
      outcome: "Insulation drift on the S3 branch; megger booked",
    },
  ],
};

const explanation18T: Explanation = {
  physics: {
    headline: "Insulation on the CBL-ADRA-S3 branch down to 0.42 MΩ; megger due in RB-31",
    state: [
      { label: "Cable insulation", value: "0.42 MΩ", baseline: "> 1.0 MΩ" },
      { label: "Relay current", value: "151 mA", baseline: "150–175 mA" },
      { label: "Feed voltage", value: "6.1 V", baseline: "6.0–6.8 V" },
    ],
    falsifier:
      "If the megger reads above 1.0 MΩ on both branches, the drop is a logger artefact and the alert returns to Watch.",
  },
  model: {
    shapTop: [
      { feature: "cable_ir_slope_7d", label: "Cable insulation slope, 7 d", value: 0.41 },
      { feature: "rain_72h", label: "Rainfall, 72 h", value: 0.16 },
      { feature: "cable_age", label: "Cable age", value: 0.09 },
    ],
    calibrationNote: "Warning band over-predicts by 3 points in wet months; ECE 0.043.",
    modeSet: ["F8", "F2"],
    modeSetCoverage: 0.88,
    agreement: "high",
  },
  precedents: [
    {
      smmsId: "SMMS-evt-731",
      assetId: "ADRA/TC/18T",
      confirmedMode: "F8",
      similarity: 0.87,
      daysAgo: 34,
      outcome: "Insulation drift on the S3 branch; megger booked",
    },
    {
      smmsId: "SMMS-evt-623",
      assetId: "TATA/TC/08T",
      confirmedMode: "F8",
      similarity: 0.7,
      daysAgo: 402,
      outcome: "Cable tail replaced",
    },
  ],
};

/* ------------------------------------------------------------------ Alerts */

type AlertSeed = Omit<Alert, "explanation" | "modelVersions" | "modeSetCoverage"> & {
  explanation: Explanation;
};

const make = (seed: AlertSeed): Alert => ({
  ...seed,
  modeSetCoverage: 0.9,
  modelVersions,
});

export const alert12T: Alert = make({
  id: "alr-7f3c",
  assetId: "ADRA/TC/12T",
  assetName: "Adra Yard · Down Goods",
  route: "Down Goods",
  division: "ADRA",
  level: "watch",
  policyRank: 2,
  persistence: 3,
  risk: { h24: 0.04, h72: 0.11, h7d: 0.24, eceZone: 0.04 },
  rul: rul(9, 21, 38),
  likelyModes: ["F1"],
  modeProbability: 0.71,
  clusterId: "c-9917",
  dataTrust: { score: 0.62, flags: ["age_vs_signature_mismatch"] },
  block: { window: win("RB-28"), fit: "fits", minutes: 90 },
  explanation: explanation12T,
  ranking: {
    calibratedRisk: 0.24,
    consequence: "high",
    consequenceNote: "Most affected member of cluster c-9917; the drain is shared with 14T and 16T",
    exposure: "Down Goods, 22 movements / day",
    trustDiscount: 0.62,
    tieBreaker: "Fits RB-28 with no extension",
  },
  ageMinutes: 192,
});

export const alertFixtures: Alert[] = [
  make({
    id: "alr-c603",
    assetId: "ADRA/TC/07T",
    assetName: "Adra Yard · Up Main",
    route: "Up Main",
    division: "ADRA",
    level: "critical",
    policyRank: 1,
    persistence: 2,
    risk: { h24: 0.52, h72: 0.68, h7d: 0.76, eceZone: 0.02 },
    rul: rul(1, 6, 14),
    likelyModes: ["F9"],
    modeProbability: 0.64,
    dataTrust: { score: 0.78, flags: ["shunt_pattern_review"] },
    // A Critical alert needs a special block; there is no published window it fits.
    explanation: explanation07T,
    ranking: {
      calibratedRisk: 0.52,
      consequence: "high",
      consequenceNote: "Wrong-side risk on a running line",
      exposure: "Up Main, 61 movements / day",
      trustDiscount: 0.78,
      tieBreaker: "No published block fits; special block needed",
    },
    ageMinutes: 21,
  }),
  alert12T,
  make({
    id: "alr-9ac1",
    assetId: "ADRA/TC/14T",
    assetName: "Adra Yard · Down Goods",
    route: "Down Goods",
    division: "ADRA",
    level: "warning",
    policyRank: 3,
    persistence: 3,
    risk: { h24: 0.18, h72: 0.34, h7d: 0.61, eceZone: 0.08 },
    rul: rul(4, 13, 25),
    likelyModes: ["F1"],
    modeProbability: 0.68,
    clusterId: "c-9917",
    dataTrust: { score: 0.84, flags: [] },
    block: { window: win("RB-29"), fit: "extends", minutes: 110 },
    explanation: explanation14T,
    ranking: {
      calibratedRisk: 0.34,
      consequence: "medium",
      consequenceNote: "Downstream of 12T in cluster c-9917",
      exposure: "Down Goods, 22 movements / day",
      trustDiscount: 0.84,
      tieBreaker: "Needs RB-29 + 20 min",
    },
    ageMinutes: 76,
  }),
  make({
    id: "alr-a735",
    assetId: "BKSC/TC/22T",
    assetName: "Bankura · Down Main",
    route: "Down Main",
    division: "BKSC",
    level: "warning",
    policyRank: 4,
    persistence: 3,
    risk: { h24: 0.12, h72: 0.31, h7d: 0.49, eceZone: 0.07 },
    rul: rul(7, 18, 34),
    likelyModes: ["F4"],
    modeProbability: 0.58,
    dataTrust: { score: 0.72, flags: [] },
    block: { window: win("RB-30"), fit: "extends", minutes: 105 },
    explanation: explanation22T,
    ranking: {
      calibratedRisk: 0.31,
      consequence: "medium",
      consequenceNote: "Points zone on a running line",
      exposure: "Down Main, 38 movements / day",
      trustDiscount: 0.72,
      tieBreaker: "Needs RB-30 + 15 min",
    },
    ageMinutes: 88,
  }),
  make({
    id: "alr-5e80",
    assetId: "ADRA/TC/16T",
    assetName: "Adra Yard · Loop Line",
    route: "Loop Line",
    division: "ADRA",
    level: "watch",
    policyRank: 5,
    persistence: 4,
    risk: { h24: 0.03, h72: 0.09, h7d: 0.27, eceZone: 0.05 },
    rul: rul(18, 31, 47),
    likelyModes: ["F4"],
    modeProbability: 0.52,
    clusterId: "c-9917",
    dataTrust: { score: 0.81, flags: [] },
    block: { window: win("RB-30"), fit: "fits", minutes: 70 },
    explanation: explanation16T,
    ranking: {
      calibratedRisk: 0.27,
      consequence: "medium",
      consequenceNote: "Member of cluster c-9917; points sit inside the drained cess",
      exposure: "Loop Line, 9 movements / day",
      trustDiscount: 0.81,
      tieBreaker: "Fits RB-30",
    },
    ageMinutes: 143,
  }),
  make({
    id: "alr-3b21",
    assetId: "ADRA/TC/21T",
    assetName: "Adra Yard · Up Goods",
    route: "Up Goods",
    division: "ADRA",
    level: "watch",
    policyRank: 6,
    persistence: 3,
    risk: { h24: 0.02, h72: 0.08, h7d: 0.22, eceZone: 0.05 },
    rul: rul(25, 42, 62),
    likelyModes: ["F1"],
    modeProbability: 0.49,
    // Primary cause is the shared cable route; the drain cluster is a predicted cascade, not a membership.
    clusterId: "c-9930",
    dataTrust: { score: 0.75, flags: ["predicted_cascade"] },
    block: { window: win("RB-32"), fit: "fits", minutes: 75 },
    explanation: explanation21T,
    ranking: {
      calibratedRisk: 0.22,
      consequence: "low",
      consequenceNote:
        "Shares cable route CBL-ADRA-S3 with 18T; predicted cascade from c-9917 in 6–11 days",
      exposure: "Up Goods, 18 movements / day",
      trustDiscount: 0.75,
      tieBreaker: "Fits RB-32",
    },
    ageMinutes: 201,
  }),
  make({
    id: "alr-6e91",
    assetId: "ADRA/TC/05T",
    assetName: "Adra Yard · Up Loop",
    route: "Up Loop",
    division: "ADRA",
    level: "watch",
    policyRank: 7,
    persistence: 5,
    risk: { h24: 0.03, h72: 0.09, h7d: 0.25, eceZone: 0.05 },
    rul: rul(14, 27, 43),
    likelyModes: ["F5"],
    modeProbability: 0.61,
    dataTrust: { score: 0.93, flags: [] },
    block: { window: win("RB-27"), fit: "fits", minutes: 60 },
    explanation: explanation05T,
    ranking: {
      calibratedRisk: 0.25,
      consequence: "low",
      consequenceNote: "Relay ageing on a loop line",
      exposure: "Up Loop, 7 movements / day",
      trustDiscount: 0.93,
      tieBreaker: "Fits RB-27",
    },
    ageMinutes: 188,
  }),
  make({
    id: "alr-1f42",
    assetId: "ADRA/TC/09T",
    assetName: "Adra Yard · Down Loop",
    route: "Down Loop",
    division: "ADRA",
    level: "watch",
    policyRank: 8,
    persistence: 3,
    risk: { h24: 0.02, h72: 0.07, h7d: 0.21, eceZone: 0.04 },
    rul: rul(24, 39, 58),
    likelyModes: ["F1"],
    modeProbability: 0.55,
    dataTrust: { score: 0.89, flags: [] },
    block: { window: win("RB-26"), fit: "fits", minutes: 65 },
    explanation: explanation09T,
    ranking: {
      calibratedRisk: 0.21,
      consequence: "low",
      consequenceNote: "Previously confirmed F1 (SMMS-evt-204)",
      exposure: "Down Loop, 8 movements / day",
      trustDiscount: 0.89,
      tieBreaker: "Fits RB-26",
    },
    ageMinutes: 306,
  }),
  make({
    id: "alr-d0c8",
    assetId: "KGP/TC/31T",
    assetName: "Kharagpur · Goods Loop",
    route: "Goods Loop",
    division: "KGP",
    level: "watch",
    policyRank: 9,
    persistence: 3,
    risk: { h24: 0.01, h72: 0.05, h7d: 0.23, eceZone: 0.04 },
    rul: rul(28, 44, 66),
    likelyModes: ["F6"],
    modeProbability: 0.47,
    dataTrust: { score: 0.66, flags: ["logger_gap_6h"] },
    // No published Kharagpur block this week; the planner shows the no-block state.
    explanation: explanation31T,
    ranking: {
      calibratedRisk: 0.23,
      consequence: "low",
      consequenceNote: "Feed instability, low traffic",
      exposure: "Goods Loop, 5 movements / day",
      trustDiscount: 0.66,
      tieBreaker: "No published block in KGP this week",
    },
    ageMinutes: 420,
  }),
  make({
    id: "alr-4c22",
    assetId: "TATA/TC/08T",
    assetName: "Tatanagar · Yard Line",
    route: "Yard Line",
    division: "TATA",
    level: "watch",
    policyRank: 10,
    persistence: 3,
    risk: { h24: 0.01, h72: 0.04, h7d: 0.2, eceZone: 0.04 },
    rul: rul(31, 48, 70),
    likelyModes: ["F8"],
    modeProbability: 0.44,
    dataTrust: { score: 0.77, flags: [] },
    block: { window: win("RB-32"), fit: "fits", minutes: 85 },
    explanation: explanation08T,
    ranking: {
      calibratedRisk: 0.2,
      consequence: "low",
      consequenceNote: "Cable insulation drift",
      exposure: "Yard Line, 6 movements / day",
      trustDiscount: 0.77,
      tieBreaker: "Fits RB-32",
    },
    ageMinutes: 515,
  }),
  make({
    id: "alr-2d17",
    assetId: "ADRA/TC/18T",
    assetName: "Adra Yard · Up Goods",
    route: "Up Goods",
    division: "ADRA",
    level: "warning",
    policyRank: 11,
    persistence: 3,
    // 72-hour risk is above the 30% Warning threshold, not exactly on it.
    risk: { h24: 0.09, h72: 0.31, h7d: 0.44, eceZone: 0.07 },
    // A bimodal cable fault: a fast tail means the published block is already outside p10.
    rul: rul(3, 22, 36),
    likelyModes: ["F8"],
    modeProbability: 0.57,
    clusterId: "c-9930",
    dataTrust: { score: 0.7, flags: [] },
    block: { window: win("RB-31"), fit: "fits", minutes: 80 },
    explanation: explanation18T,
    ranking: {
      calibratedRisk: 0.31,
      consequence: "medium",
      consequenceNote: "Cable route shared with 21T",
      exposure: "Up Goods, 18 movements / day",
      trustDiscount: 0.7,
      tieBreaker: "Fits RB-31",
    },
    ageMinutes: 980,
    deferral: {
      reason: "Cable megger test already booked with S&T crew in RB-31",
      reviewDate: "2026-07-19",
    },
  }),
];

/* ------------------------------------------------------------------ Asset records */

export interface AssetRecord {
  id: string;
  lengthM: number;
  circuitType: "DC" | "AC";
  installed: string;
  codalLifeYears: number;
  relay: string;
  supply: string;
  cable: string;
  relayRoom: string;
  weatherCell: string;
  provenance: string;
}

const record = (seed: Omit<AssetRecord, "provenance">): AssetRecord => ({
  ...seed,
  provenance: "SMMS asset register + track-circuit telemetry · demo fixture",
});

export const assetRecords: Record<string, AssetRecord> = {
  "ADRA/TC/12T": record({
    id: "ADRA/TC/12T",
    lengthM: 420,
    circuitType: "DC",
    installed: "2009-03-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR12",
    supply: "XYZ/IPS/1",
    cable: "XYZ/CBL/N2",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "ADRA/TC/07T": record({
    id: "ADRA/TC/07T",
    lengthM: 380,
    circuitType: "DC",
    installed: "2011-06-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR07",
    supply: "XYZ/IPS/1",
    cable: "XYZ/CBL/N1",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "ADRA/TC/14T": record({
    id: "ADRA/TC/14T",
    lengthM: 380,
    circuitType: "DC",
    installed: "2010-02-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR14",
    supply: "XYZ/IPS/1",
    cable: "XYZ/CBL/N2",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "ADRA/TC/16T": record({
    id: "ADRA/TC/16T",
    lengthM: 260,
    circuitType: "DC",
    installed: "2012-09-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR16",
    supply: "XYZ/IPS/2",
    cable: "XYZ/CBL/N3",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "ADRA/TC/21T": record({
    id: "ADRA/TC/21T",
    lengthM: 340,
    circuitType: "DC",
    installed: "2013-01-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR21",
    supply: "XYZ/IPS/2",
    cable: "XYZ/CBL/S3",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "ADRA/TC/18T": record({
    id: "ADRA/TC/18T",
    lengthM: 410,
    circuitType: "DC",
    installed: "2008-11-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR18",
    supply: "XYZ/IPS/2",
    cable: "XYZ/CBL/S3",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "ADRA/TC/05T": record({
    id: "ADRA/TC/05T",
    lengthM: 300,
    circuitType: "DC",
    installed: "2007-04-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR05",
    supply: "XYZ/IPS/1",
    cable: "XYZ/CBL/N4",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "ADRA/TC/09T": record({
    id: "ADRA/TC/09T",
    lengthM: 360,
    circuitType: "DC",
    installed: "2014-03-01",
    codalLifeYears: 15,
    relay: "XYZ/RLY/TR09",
    supply: "XYZ/IPS/1",
    cable: "XYZ/CBL/N2",
    relayRoom: "XYZ/RR/1",
    weatherCell: "wx-20.30N-85.83E",
  }),
  "BKSC/TC/22T": record({
    id: "BKSC/TC/22T",
    lengthM: 520,
    circuitType: "AC",
    installed: "2016-08-01",
    codalLifeYears: 20,
    relay: "BKS/RLY/TR22",
    supply: "BKS/IPS/1",
    cable: "BKS/CBL/E1",
    relayRoom: "BKS/RR/2",
    weatherCell: "wx-23.24N-87.07E",
  }),
  "KGP/TC/31T": record({
    id: "KGP/TC/31T",
    lengthM: 480,
    circuitType: "AC",
    installed: "2012-05-01",
    codalLifeYears: 20,
    relay: "KGP/RLY/TR31",
    supply: "KGP/IPS/2",
    cable: "KGP/CBL/W2",
    relayRoom: "KGP/RR/1",
    weatherCell: "wx-22.33N-87.32E",
  }),
  "TATA/TC/08T": record({
    id: "TATA/TC/08T",
    lengthM: 400,
    circuitType: "DC",
    installed: "2015-10-01",
    codalLifeYears: 15,
    relay: "TAT/RLY/TR08",
    supply: "TAT/IPS/1",
    cable: "TAT/CBL/Y1",
    relayRoom: "TAT/RR/3",
    weatherCell: "wx-22.80N-86.20E",
  }),
};

export const assetRecord = assetRecords["ADRA/TC/12T"]!;

/* ------------------------------------------------------------------ Signals */

export interface SignalSeries {
  key: string;
  label: string;
  unit: string;
  baseline: number;
  normalBand: string;
  values: number[];
}

/** 12 daily readings, oldest first, for ADRA/TC/12T. The last point is the field task's "last reading". */
export const signalFixtures: SignalSeries[] = [
  {
    key: "relay_i",
    label: "Relay current",
    unit: "mA",
    baseline: 162,
    normalBand: "150–175 mA",
    values: [162, 161, 158, 156, 152, 148, 144, 139, 134, 129, 124, 118],
  },
  {
    key: "ballast_g",
    label: "Ballast conductance",
    unit: "× dry",
    baseline: 1,
    normalBand: "0.9–1.1 × dry",
    values: [1, 1.02, 1.03, 1.05, 1.08, 1.11, 1.14, 1.18, 1.21, 1.25, 1.28, 1.31],
  },
  {
    key: "feed_v",
    label: "Feed voltage",
    unit: "V",
    baseline: 6.4,
    normalBand: "6.0–6.8 V",
    values: [6.4, 6.4, 6.3, 6.4, 6.3, 6.3, 6.2, 6.3, 6.2, 6.2, 6.2, 6.1],
  },
  {
    key: "cable_ir",
    label: "Cable insulation",
    unit: "MΩ",
    baseline: 1.2,
    normalBand: "> 1.0 MΩ",
    values: [1.2, 1.2, 1.15, 1.1, 1.02, 0.96, 0.9, 0.84, 0.78, 0.72, 0.66, 0.6],
  },
];

export const modeDistribution: {
  code: FailureModeCode;
  probability: number;
  inSet: boolean;
  excluded?: string;
}[] = [
  { code: "F1", probability: 0.71, inSet: true },
  { code: "F4", probability: 0.17, inSet: true },
  {
    code: "F2",
    probability: 0.06,
    inSet: false,
    excluded: "Joint insulation 0.6 MΩ is still above the 0.5 MΩ falsifier",
  },
  {
    code: "F5",
    probability: 0.03,
    inSet: false,
    excluded: "Relay XYZ/RLY/TR12 drop-away tested in spec on 02 Jun",
  },
];

/* ------------------------------------------------------------------ Per-asset signal history
 * Every circuit gets a 12-day history so no asset page is a dead end. The series a circuit
 * carries depend on its likely failure mode (a shunt failure shows drop-away and shunt
 * resistance, a cable fault shows insulation), the endpoint is taken from the alert's own
 * explanation when it states one, and the trend is deterministic per asset, so the same
 * alert always renders the same chart.
 */

interface SeriesSpec {
  key: string;
  label: string;
  unit: string;
  baseline: number;
  normalBand: string;
  dp: number;
  magnitude: number;
  direction: 1 | -1;
  /** Physics-state label fragment whose value should be used as the endpoint. */
  match: string;
  /** Failure modes for which this signal is a primary signature. */
  modes: FailureModeCode[];
}

const relaySeries: SeriesSpec = {
  key: "relay_i",
  label: "Relay current",
  unit: "mA",
  baseline: 162,
  normalBand: "150–175 mA",
  dp: 0,
  magnitude: 30,
  direction: -1,
  match: "relay current",
  modes: ["F1", "F3", "F10"],
};
const ballastSeries: SeriesSpec = {
  key: "ballast_g",
  label: "Ballast conductance",
  unit: "× dry",
  baseline: 1,
  normalBand: "0.9–1.1 × dry",
  dp: 2,
  magnitude: 0.3,
  direction: 1,
  match: "ballast conductance",
  modes: ["F1", "F2", "F4"],
};
const feedSeries: SeriesSpec = {
  key: "feed_v",
  label: "Feed voltage",
  unit: "V",
  baseline: 6.4,
  normalBand: "6.0–6.8 V",
  dp: 1,
  magnitude: 0.5,
  direction: -1,
  match: "feed voltage",
  modes: ["F6", "F7"],
};
const cableSeries: SeriesSpec = {
  key: "cable_ir",
  label: "Cable insulation",
  unit: "MΩ",
  baseline: 1.2,
  normalBand: "> 1.0 MΩ",
  dp: 2,
  magnitude: 0.5,
  direction: -1,
  match: "cable insulation",
  modes: ["F2", "F8"],
};
const dropAwaySeries: SeriesSpec = {
  key: "drop_away",
  label: "Drop-away delay",
  unit: "s",
  baseline: 0.3,
  normalBand: "< 0.5 s",
  dp: 1,
  magnitude: 1.4,
  direction: 1,
  match: "drop-away",
  modes: ["F9"],
};
const shuntSeries: SeriesSpec = {
  key: "shunt_sens",
  label: "Shunt sensitivity",
  unit: "Ω",
  baseline: 0.5,
  normalBand: "0.5 Ω design",
  dp: 2,
  magnitude: 0.18,
  direction: -1,
  match: "shunt sensitivity",
  modes: ["F9"],
};
const pickupSeries: SeriesSpec = {
  key: "relay_pickup",
  label: "Pick-up current",
  unit: "× commissioning",
  baseline: 1,
  normalBand: "< 1.05 ×",
  dp: 2,
  magnitude: 0.12,
  direction: 1,
  match: "pick-up current",
  modes: ["F5"],
};

/** Which signals matter for each likely mode; a flat set is better than a misleading one. */
const seriesForMode: Record<FailureModeCode, SeriesSpec[]> = {
  F1: [relaySeries, ballastSeries, cableSeries],
  F2: [cableSeries, ballastSeries, relaySeries],
  F3: [relaySeries, ballastSeries],
  F4: [ballastSeries, relaySeries],
  F5: [pickupSeries, relaySeries],
  F6: [feedSeries, relaySeries],
  F7: [feedSeries, relaySeries],
  F8: [cableSeries, feedSeries],
  F9: [dropAwaySeries, shuntSeries, ballastSeries],
  F10: [relaySeries, ballastSeries],
  F11: [relaySeries, ballastSeries, feedSeries],
  F12: [relaySeries, ballastSeries],
};

/** Deterministic per-asset noise so two circuits of the same mode do not share a chart. */
function seededRandom(seed: string): () => number {
  let h = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    h ^= seed.charCodeAt(index);
    h = Math.imul(h, 16777619);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

/** Reads an explicitly stated value out of the physics state, e.g. "118 mA" -> 118. */
function statedValue(alert: Alert, match: string): number | null {
  const entry = alert.explanation.physics.state.find((item) =>
    item.label.toLowerCase().includes(match),
  );
  if (!entry) return null;
  const found = entry.value.match(/-?\d+(?:\.\d+)?/);
  return found ? Number(found[0]) : null;
}

const RISK_LOOKBACK = 0.6;

/** Maps a signal key to the matching field-task reading. */
const fieldReadingKey: Record<string, keyof FieldTask["lastReadings"]> = {
  relay_i: "relayCurrent",
  ballast_g: "ballastConductance",
  cable_ir: "cableInsulation",
  feed_v: "feedVoltage",
};

/**
 * The value a field crew already recorded for this circuit, so a chart and the field
 * task it belongs to can never disagree. Evaluated after `fieldTaskFixtures` is built.
 */
function fieldReading(assetId: string, key: string): number | null {
  const task = fieldTaskFixtures.find((item) => item.assetId === assetId);
  const readingKey = fieldReadingKey[key];
  if (!task || !readingKey) return null;
  const value = Number(task.lastReadings[readingKey]);
  return Number.isFinite(value) ? value : null;
}

function buildSeries(
  spec: SeriesSpec,
  alert: Alert,
  primary: FailureModeCode,
  random: () => number,
): SignalSeries {
  const risk = Math.min(
    1,
    Math.max(alert.risk.h24, alert.risk.h72, alert.risk.h7d) / RISK_LOOKBACK,
  );
  const stated = statedValue(alert, spec.match);
  const primaryFor = spec.modes.includes(primary);
  // Preference order: a value the explanation states, then a value a field crew already
  // recorded, then a mode-appropriate trend. A signal that is not a signature of this mode
  // drifts only slightly, so the chart never implies evidence the model does not have.
  const end =
    stated ??
    fieldReading(alert.assetId, spec.key) ??
    spec.baseline + spec.direction * spec.magnitude * risk * (primaryFor ? 1 : 0.12);
  const phase = random() * Math.PI * 2;
  const points = 12;
  const values = Array.from({ length: points }, (_, index) => {
    const t = index / (points - 1);
    const trend = spec.baseline + (end - spec.baseline) * t;
    const wiggle = spec.direction * spec.magnitude * 0.05 * Math.sin(index * 1.6 + phase) * (1 - t);
    return Number((trend + wiggle).toFixed(spec.dp));
  });
  values[points - 1] = Number(end.toFixed(spec.dp));
  return {
    key: spec.key,
    label: spec.label,
    unit: spec.unit,
    baseline: spec.baseline,
    normalBand: spec.normalBand,
    values,
  };
}

/* ------------------------------------------------------------------ Per-asset mode distribution */

export interface ModeRow {
  code: FailureModeCode;
  probability: number;
  inSet: boolean;
  excluded?: string;
}

export const modeDistributionByAsset: Record<string, ModeRow[]> = Object.fromEntries(
  alertFixtures.map((alert) => {
    const primary = alert.likelyModes[0] ?? "F12";
    const alternatives = alert.explanation.model.modeSet.filter((code) => code !== primary);
    const remaining = Math.max(0, 1 - alert.modeProbability);
    // Harmonic weights keep the first alternative ahead of the rest.
    const weights = alternatives.map((_, index) => 1 / (index + 1));
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    const rows: ModeRow[] = [
      { code: primary, probability: alert.modeProbability, inSet: true },
      ...alternatives.map((code, index) => ({
        code,
        probability: total > 0 ? (remaining * (weights[index] ?? 0)) / total : 0,
        inSet: true,
      })),
    ];
    // A single-mode conformal set still leaves residual probability unclassified.
    if (alternatives.length === 0 && remaining > 0) {
      rows.push({
        code: "F12",
        probability: remaining,
        inSet: false,
        excluded: "Residual mass stays no-fault-found until the falsifier is checked",
      });
    }
    return [alert.assetId, rows];
  }),
);
modeDistributionByAsset["ADRA/TC/12T"] = modeDistribution;

/* ------------------------------------------------------------------ Clusters
 * Membership is derived from `Alert.clusterId`, so the cluster card, the queue
 * filter and the asset page cannot disagree.
 */

export interface Cluster {
  id: string;
  title: string;
  state: "open" | "monitoring";
  summary: string;
  alertsFolded: number;
  decisions: { title: string; assets: string[]; blockId: string | null }[];
  savedBlockHours: number;
  weatherCell: string;
  sharedEdges: { kind: string; id: string; note: string }[];
  members: string[];
  predictedCascade?: { assetId: string; inDays: { min: number; max: number } };
}

type ClusterSeed = Omit<Cluster, "members" | "alertsFolded">;

const cluster = (seed: ClusterSeed): Cluster => {
  const members = alertFixtures
    .filter((alert) => alert.clusterId === seed.id)
    .map((alert) => alert.assetId);
  return { ...seed, members, alertsFolded: members.length };
};

export const clusterFixtures: Cluster[] = [
  cluster({
    id: "c-9917",
    title: "Drain / weather cell",
    state: "open",
    summary:
      "Three alerts on the Down Goods drain share one physical cause; one crew can clear all three.",
    decisions: [
      {
        title: "Ballast clearing + drain rodding at 12T",
        assets: ["ADRA/TC/12T"],
        blockId: "RB-28",
      },
      { title: "Drain rodding, Down Goods cess at 14T", assets: ["ADRA/TC/14T"], blockId: "RB-29" },
      { title: "Points bridging check at 16T", assets: ["ADRA/TC/16T"], blockId: "RB-30" },
    ],
    savedBlockHours: 1.2,
    weatherCell: "wx-20.30N-85.83E",
    sharedEdges: [
      {
        kind: "Weather cell",
        id: "wx-20.30N-85.83E",
        note: "96 mm rain in 72 h against a 22 mm median",
      },
      { kind: "Drain", id: "DR-ADRA-04", note: "Cess drain along Down Goods, last rodded 11 Mar" },
      {
        kind: "Relay room",
        id: "XYZ/RR/1",
        note: "Shared relay room; no common supply fault seen",
      },
    ],
    predictedCascade: { assetId: "ADRA/TC/21T", inDays: { min: 6, max: 11 } },
  }),
  cluster({
    id: "c-9930",
    title: "Up Goods cable route",
    state: "monitoring",
    summary: "Two alerts share cable route CBL-ADRA-S3; one megger covers both branches.",
    decisions: [
      {
        title: "Megger test on CBL-ADRA-S3",
        assets: ["ADRA/TC/18T", "ADRA/TC/21T"],
        blockId: "RB-31",
      },
    ],
    savedBlockHours: 0.5,
    weatherCell: "wx-20.30N-85.83E",
    sharedEdges: [
      {
        kind: "Cable route",
        id: "CBL-ADRA-S3",
        note: "Insulation drift on two branches since 02 Jul",
      },
    ],
  }),
];
export const clusterFixture = clusterFixtures[0]!;

/* ------------------------------------------------------------------ Blocks */

export interface BlockJob {
  id: string;
  title: string;
  assets: string[];
  blockId: string | null;
  durationMin: number;
  fit: BlockFit;
  crew: string;
}

export const blockJobs: BlockJob[] = [
  {
    id: "job-01",
    title: "Rail head cleaning + 0.5 Ω shunt test",
    assets: ["ADRA/TC/07T"],
    blockId: null,
    durationMin: 120,
    fit: "special",
    crew: "ESM gang 2",
  },
  {
    id: "job-02",
    title: "Ballast clearing + drain rodding",
    assets: ["ADRA/TC/12T"],
    blockId: "RB-28",
    durationMin: 90,
    fit: "fits",
    crew: "ESM gang 1 + PWay",
  },
  {
    id: "job-03",
    title: "Drain rodding, Down Goods cess",
    assets: ["ADRA/TC/14T"],
    blockId: "RB-29",
    durationMin: 110,
    fit: "extends",
    crew: "PWay gang 4",
  },
  {
    id: "job-04",
    title: "Points bridging check",
    assets: ["ADRA/TC/16T"],
    blockId: "RB-30",
    durationMin: 70,
    fit: "fits",
    crew: "ESM gang 1",
  },
  {
    id: "job-05",
    title: "Relay drop-away test",
    assets: ["ADRA/TC/05T"],
    blockId: "RB-27",
    durationMin: 60,
    fit: "fits",
    crew: "ESM gang 3",
  },
  {
    id: "job-06",
    title: "Ballast resistance check",
    assets: ["ADRA/TC/09T"],
    blockId: "RB-26",
    durationMin: 65,
    fit: "fits",
    crew: "ESM gang 3",
  },
  {
    id: "job-07",
    title: "Megger test, cable route S3",
    assets: ["ADRA/TC/18T", "ADRA/TC/21T"],
    blockId: "RB-31",
    durationMin: 80,
    fit: "fits",
    crew: "S&T cable crew",
  },
  {
    id: "job-08",
    title: "Feed stability check",
    assets: ["KGP/TC/31T"],
    blockId: null,
    durationMin: 90,
    fit: "none",
    crew: "KGP ESM",
  },
];

/* ------------------------------------------------------------------ Summary fixtures */

export const kpiFixture = {
  openAlerts: { value: 11, delta: "+2 since yesterday" },
  criticalShift: { value: 1, delta: "07T · 21 min" },
  clusterAdjusted: { value: 5, delta: "5 alerts → 4 jobs" },
  blockFit: { value: 0.78, delta: "+6 pts wk 28" },
  queue: { open: 11, critical: 1, warning: 3, watch: 7, medianAgeHours: 3.2 },
};

export const modelHealthFixture = {
  asOf: "13 Jul 2026 · 23:00 IST",
  window: "01 Apr – 30 Jun 2026 · 3,180 held-out outcomes",
  ece: 0.031,
  eceBins: 10,
  coverage: 0.897,
  heldOutN: 3180,
  activeModels: 5,
  driftAmber: 1,
  models: [
    {
      name: "Physics twin",
      version: "0.3.1",
      trained: "28 May 2026",
      window: "Jan 2023 – Apr 2026",
      owner: "S&T R&D",
      state: "Active",
    },
    {
      name: "Propagation GNN",
      version: "0.2.0",
      trained: "02 Jun 2026",
      window: "Jan 2024 – May 2026",
      owner: "ML platform",
      state: "Active",
    },
    {
      name: "Survival / RUL",
      version: "0.2.4",
      trained: "09 Jun 2026",
      window: "Jan 2022 – May 2026",
      owner: "ML platform",
      state: "Active",
    },
    {
      name: "Mode classifier",
      version: "0.2.0",
      trained: "02 Jun 2026",
      window: "Jan 2023 – May 2026",
      owner: "ML platform",
      state: "Active",
    },
    {
      name: "Conformal calibrator",
      version: "0.1.3",
      trained: "30 Jun 2026",
      window: "Apr – Jun 2026",
      owner: "ML platform",
      state: "Active",
    },
  ],
  reliability: [
    { predicted: 0.05, observed: 0.04, n: 640 },
    { predicted: 0.15, observed: 0.14, n: 812 },
    { predicted: 0.25, observed: 0.23, n: 498 },
    { predicted: 0.35, observed: 0.33, n: 361 },
    { predicted: 0.45, observed: 0.44, n: 284 },
    { predicted: 0.55, observed: 0.51, n: 221 },
    { predicted: 0.65, observed: 0.61, n: 168 },
    { predicted: 0.75, observed: 0.7, n: 112 },
    { predicted: 0.85, observed: 0.79, n: 58 },
    { predicted: 0.95, observed: 0.88, n: 26 },
  ],
  byLevel: [
    { level: "watch" as const, predicted: 0.24, observed: 0.22, n: 2410, leadTime: "18 d median" },
    { level: "warning" as const, predicted: 0.38, observed: 0.36, n: 612, leadTime: "6 d median" },
    {
      level: "critical" as const,
      predicted: 0.56,
      observed: 0.47,
      n: 158,
      leadTime: "19 h median",
    },
  ],
  byMode: [
    { code: "F1" as FailureModeCode, precision: 0.84, recall: 0.81, n: 1204 },
    { code: "F2" as FailureModeCode, precision: 0.77, recall: 0.72, n: 418 },
    { code: "F3" as FailureModeCode, precision: 0.8, recall: 0.69, n: 301 },
    { code: "F4" as FailureModeCode, precision: 0.73, recall: 0.7, n: 389 },
    { code: "F5" as FailureModeCode, precision: 0.82, recall: 0.78, n: 512 },
    { code: "F6" as FailureModeCode, precision: 0.61, recall: 0.58, n: 147 },
  ],
  drift: [
    { name: "Rainfall distribution", psi: 0.18, threshold: 0.2, state: "warning" as const },
    { name: "Relay current", psi: 0.09, threshold: 0.2, state: "nominal" as const },
    { name: "Asset age mix", psi: 0.06, threshold: 0.2, state: "nominal" as const },
    { name: "Traffic density", psi: 0.04, threshold: 0.2, state: "nominal" as const },
  ],
  dataTrust: {
    division: 0.81,
    lowTrustAssets: 2,
    flags: [
      { flag: "logger_gap_6h", count: 4 },
      { flag: "age_vs_signature_mismatch", count: 1 },
      { flag: "shunt_pattern_review", count: 1 },
      { flag: "predicted_cascade", count: 1 },
    ],
  },
  gates: [
    { name: "Calibration", rule: "ECE ≤ 0.05 over 10 bins", value: "0.031", pass: true },
    { name: "Coverage", rule: "Conformal coverage 0.88–0.92", value: "0.897", pass: true },
    {
      name: "Subgroup parity",
      rule: "Coverage gap ≤ 0.04 across divisions",
      value: "0.027",
      pass: true,
    },
    {
      name: "Shadow period",
      rule: "≥ 28 days in shadow before promotion",
      value: "34 days",
      pass: true,
    },
  ],
  signature:
    "Reviewed by Sr DSTE/ADRA and ML platform lead · 30 Jun 2026 · registry entry REG-2026-0630",
};

/* ------------------------------------------------------------------ Field */

export interface FieldTask {
  id: string;
  assetId: string;
  title: string;
  titleHi: string;
  route: string;
  lengthM: number;
  blockId: string;
  date: string;
  start: string;
  end: string;
  level: AlertLevel;
  hypothesis: string;
  hypothesisHi: string;
  falsifier: string;
  falsifierHi: string;
  lastReadings: {
    relayCurrent: string;
    ballastConductance: string;
    cableInsulation: string;
    feedVoltage: string;
  };
}

export const fieldTaskFixtures: FieldTask[] = [
  {
    id: "task-12t",
    assetId: "ADRA/TC/12T",
    title: "Inspect ballast and cess drain",
    titleHi: "बैलास्ट और नाली की जाँच",
    route: "Down Goods",
    lengthM: 420,
    blockId: "RB-28",
    date: "2026-07-16",
    start: "02:10",
    end: "03:40",
    level: "watch",
    hypothesis: "Wet, fouled ballast is lowering ballast resistance (F1).",
    hypothesisHi: "गीला, गंदा बैलास्ट बैलास्ट प्रतिरोध घटा रहा है (F1)।",
    falsifier:
      "If cable insulation is below 0.5 MΩ, record it — the cause is likely the joint (F2), not F1.",
    falsifierHi:
      "यदि केबल इंसुलेशन 0.5 MΩ से कम है, तो दर्ज करें — कारण जोड़ (F2) हो सकता है, F1 नहीं।",
    // Matches the last point of signalFixtures for 12T.
    lastReadings: {
      relayCurrent: "118",
      ballastConductance: "1.31",
      cableInsulation: "0.6",
      feedVoltage: "6.1",
    },
  },
  {
    id: "task-14t",
    assetId: "ADRA/TC/14T",
    title: "Rod cess drain, Down Goods",
    titleHi: "डाउन गुड्स नाली की सफ़ाई",
    route: "Down Goods",
    lengthM: 380,
    blockId: "RB-29",
    date: "2026-07-17",
    start: "01:50",
    end: "03:20",
    level: "warning",
    hypothesis: "Blocked cess drain keeps ballast saturated (F1).",
    hypothesisHi: "बंद नाली के कारण बैलास्ट भीगा रहता है (F1)।",
    falsifier:
      "If the drain runs clear and relay current is above 150 mA, the cause is not drainage.",
    falsifierHi: "यदि नाली साफ़ बहती है और रिले करंट 150 mA से ऊपर है, तो कारण जल निकासी नहीं है।",
    lastReadings: {
      relayCurrent: "131",
      ballastConductance: "1.27",
      cableInsulation: "1.1",
      feedVoltage: "6.3",
    },
  },
  {
    id: "task-16t",
    assetId: "ADRA/TC/16T",
    title: "Check points for metallic bridging",
    titleHi: "पॉइंट्स पर धातु ब्रिजिंग की जाँच",
    route: "Loop Line",
    lengthM: 260,
    blockId: "RB-30",
    date: "2026-07-18",
    start: "02:00",
    end: "03:30",
    level: "watch",
    hypothesis: "Metal debris near the points is bridging the rails (F4).",
    hypothesisHi: "पॉइंट्स के पास धातु का मलबा रेलों को जोड़ रहा है (F4)।",
    falsifier: "If no debris is found and ballast is dry, re-rank toward F1.",
    falsifierHi: "यदि कोई मलबा नहीं मिलता और बैलास्ट सूखा है, तो F1 की ओर पुनः क्रम दें।",
    lastReadings: {
      relayCurrent: "149",
      ballastConductance: "1.08",
      cableInsulation: "1.3",
      feedVoltage: "6.4",
    },
  },
];

/* ------------------------------------------------------------------ Per-asset signal history
 * Built after the field tasks so a chart can end on the reading a crew already recorded.
 */

export const signalFixturesByAsset: Record<string, SignalSeries[]> = Object.fromEntries(
  alertFixtures.map((alert) => {
    const random = seededRandom(alert.assetId);
    const primary = alert.likelyModes[0] ?? "F12";
    const specs = seriesForMode[primary].slice(0, 4);
    return [alert.assetId, specs.map((spec) => buildSeries(spec, alert, primary, random))];
  }),
);
// 12T keeps the hand-authored history its field task is checked against.
signalFixturesByAsset["ADRA/TC/12T"] = signalFixtures;

export const fieldSyncFixture = { lastSync: "13 Jul · 23:52 IST", queuedOffline: 3 };

export const searchIndex = {
  smms: [
    "SMMS-evt-091",
    "SMMS-evt-118",
    "SMMS-evt-204",
    "SMMS-evt-377",
    "SMMS-evt-412",
    "SMMS-evt-455",
    "SMMS-evt-508",
    "SMMS-evt-623",
    "SMMS-evt-731",
    "SMMS-evt-733",
    "SMMS-evt-845",
    "SMMS-evt-902",
  ],
};
