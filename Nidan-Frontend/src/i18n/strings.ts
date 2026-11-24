import { useUi, type Lang } from "@/stores/ui";

/**
 * Bilingual bundles (en, hi). Coverage: navigation, field tasks, confirmations, errors and safety copy.
 * Model metrics, SHAP labels and identifiers stay English by design.
 */
const en = {
  "nav.home": "Command centre",
  "nav.homeShort": "Home",
  "nav.alerts": "Alert queue",
  "nav.alertsShort": "Alerts",
  "nav.asset": "Circuit detail",
  "nav.assetShort": "Asset",
  "nav.clusters": "Common cause",
  "nav.blocks": "Rolling Block",
  "nav.models": "Model health",
  "nav.modelsShort": "Models",
  "nav.field": "Field app",
  "nav.fieldShort": "Field",
  "nav.design": "Design system",
  "nav.review": "Evidence review",
  "nav.reviewShort": "Review",
  "nav.more": "More",
  "nav.operate": "Operate",
  "nav.assure": "Assure",
  "nav.reference": "Reference",
  "safety.advisory": "Advisory · non-vital",
  "safety.statement":
    "NIDAN is advisory. It has no write path to interlocking, signals, routes or track circuits.",
  "safety.fieldTheme":
    "The field app always uses a high-contrast light surface for sunlight, whatever your Day/Night choice.",
  "theme.day": "Day",
  "theme.night": "Night",
  "theme.label": "Theme",
  "search.placeholder": "Search assets, alerts, clusters, SMMS IDs…",
  "search.open": "Search",
  "error.retry": "Retry",
  "error.panel": "This panel didn't load. Other panels are unaffected.",
  "field.tasks": "My tasks",
  "field.task": "Task",
  "field.block": "Block",
  "field.hypothesis": "What NIDAN thinks",
  "field.falsifier": "What would prove it wrong",
  "field.step1": "Measurements",
  "field.step2": "Finding",
  "field.step3": "Confirm",
  "field.relayCurrent": "Relay current",
  "field.ballast": "Ballast conductance",
  "field.cable": "Cable insulation",
  "field.feed": "Feed voltage",
  "field.useLast": "Use last reading",
  "field.photo": "Add photo of ballast crib",
  "field.confirmed": "Confirmed",
  "field.confirmedHint": "The physical cause is as described",
  "field.notFound": "Not found",
  "field.notFoundHint": "Nothing matching the hypothesis",
  "field.somethingElse": "Something else",
  "field.somethingElseHint": "A different cause — describe it",
  "field.note": "What you saw",
  "field.summary": "This will be written to the SMMS draft",
  "field.queue": "Queue offline",
  "field.queueContinue": "Queue & continue",
  "field.saveDraft": "Save draft",
  "field.lastSync": "Last sync",
  "field.queued": "queued offline",
  "field.offline": "Offline",
  "field.online": "Online",
  "field.saved": "Saved on this device. It will sync when signal returns.",
  "field.queuedToast": "Queued on this device. Not yet in SMMS.",
  "field.required": "Choose a finding before confirming.",
  "field.open": "Open task",
  "field.back": "Back to tasks",
  "field.noTasks": "No tasks assigned",
} as const;

export type StringKey = keyof typeof en;

const hi: Record<StringKey, string> = {
  "nav.home": "कमांड केंद्र",
  "nav.homeShort": "होम",
  "nav.alerts": "अलर्ट कतार",
  "nav.alertsShort": "अलर्ट",
  "nav.asset": "सर्किट विवरण",
  "nav.assetShort": "एसेट",
  "nav.clusters": "साझा कारण",
  "nav.blocks": "रोलिंग ब्लॉक",
  "nav.models": "मॉडल स्थिति",
  "nav.modelsShort": "मॉडल",
  "nav.field": "फ़ील्ड ऐप",
  "nav.fieldShort": "फ़ील्ड",
  "nav.design": "डिज़ाइन सिस्टम",
  "nav.review": "साक्ष्य समीक्षा",
  "nav.reviewShort": "समीक्षा",
  "nav.more": "और",
  "nav.operate": "संचालन",
  "nav.assure": "आश्वासन",
  "nav.reference": "संदर्भ",
  "safety.advisory": "परामर्शी · गैर-महत्वपूर्ण",
  "safety.statement":
    "NIDAN केवल परामर्शी है। इंटरलॉकिंग, सिग्नल, रूट या ट्रैक सर्किट पर इसका कोई नियंत्रण नहीं है।",
  "safety.fieldTheme":
    "धूप में पढ़ने के लिए फ़ील्ड ऐप हमेशा उच्च-कंट्रास्ट हल्की सतह का उपयोग करता है।",
  "theme.day": "दिन",
  "theme.night": "रात",
  "theme.label": "थीम",
  "search.placeholder": "एसेट, अलर्ट, क्लस्टर, SMMS ID खोजें…",
  "search.open": "खोजें",
  "error.retry": "फिर से प्रयास करें",
  "error.panel": "यह पैनल लोड नहीं हुआ। अन्य पैनल प्रभावित नहीं हैं।",
  "field.tasks": "मेरे कार्य",
  "field.task": "कार्य",
  "field.block": "ब्लॉक",
  "field.hypothesis": "NIDAN का अनुमान",
  "field.falsifier": "क्या इसे गलत साबित करेगा",
  "field.step1": "माप",
  "field.step2": "निष्कर्ष",
  "field.step3": "पुष्टि",
  "field.relayCurrent": "रिले करंट",
  "field.ballast": "बैलास्ट चालकता",
  "field.cable": "केबल इंसुलेशन",
  "field.feed": "फ़ीड वोल्टेज",
  "field.useLast": "पिछली रीडिंग लें",
  "field.photo": "बैलास्ट की फ़ोटो जोड़ें",
  "field.confirmed": "पुष्टि हुई",
  "field.confirmedHint": "भौतिक कारण वर्णन के अनुसार है",
  "field.notFound": "नहीं मिला",
  "field.notFoundHint": "अनुमान से मेल खाता कुछ नहीं",
  "field.somethingElse": "कुछ और",
  "field.somethingElseHint": "अलग कारण — वर्णन करें",
  "field.note": "आपने क्या देखा",
  "field.summary": "यह SMMS ड्राफ़्ट में लिखा जाएगा",
  "field.queue": "ऑफ़लाइन कतार में रखें",
  "field.queueContinue": "कतार में रखें और आगे बढ़ें",
  "field.saveDraft": "ड्राफ़्ट सहेजें",
  "field.lastSync": "अंतिम सिंक",
  "field.queued": "ऑफ़लाइन कतार में",
  "field.offline": "ऑफ़लाइन",
  "field.online": "ऑनलाइन",
  "field.saved": "इस डिवाइस पर सहेजा गया। सिग्नल आने पर सिंक होगा।",
  "field.queuedToast": "इस डिवाइस पर कतार में। अभी SMMS में नहीं।",
  "field.required": "पुष्टि से पहले निष्कर्ष चुनें।",
  "field.open": "कार्य खोलें",
  "field.back": "कार्यों पर वापस",
  "field.noTasks": "कोई कार्य नहीं",
};

export const bundles: Record<Lang, Record<StringKey, string>> = { en, hi };

export function translate(lang: Lang, key: StringKey) {
  return bundles[lang][key];
}

/** Returns t(key) and the active language; wrap Hindi output in an element with lang="hi". */
export function useT() {
  const lang = useUi((state) => state.lang);
  return { lang, t: (key: StringKey) => bundles[lang][key] };
}

/*
 * Language is applied after hydration, because the server cannot know a saved choice.
 * `<html lang>` is updated in the same effect as the bundle (see `__root.tsx`), so the
 * attribute always matches the language actually on screen: English text is never
 * announced under a Hindi tag, and vice versa.
 */
