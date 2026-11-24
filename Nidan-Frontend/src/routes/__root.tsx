import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  useRouterState,
  HeadContent,
  Scripts,
  type ErrorComponentProps,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Toaster } from "sonner";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { themeBootScript, useTheme } from "@/lib/theme";
import { ControlShell } from "@/components/shell/ControlShell";
import { LANG_STORAGE_KEY, useUi } from "@/stores/ui";
import { alertsQuery, clustersQuery } from "@/lib/queries";

function NotFoundComponent() {
  return (
    <div className="flex min-h-[60dvh] items-center justify-center px-4">
      <div className="max-w-md text-center">
        <p className="eyebrow">404</p>
        <h1 className="mt-2 font-display text-2xl font-semibold text-text-hi">
          This page isn't part of NIDAN
        </h1>
        <p className="mt-2 text-sm text-text-mid">
          The address may be mistyped, or the asset is not in the demo dataset.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex min-h-11 items-center justify-center rounded-sm bg-accent-text px-4 text-sm font-semibold text-on-accent hover:opacity-90"
          >
            Back to command centre
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: ErrorComponentProps) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-[60dvh] items-center justify-center px-4">
      <div role="alert" className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-text-hi">This page didn't load</h1>
        <p className="mt-2 text-sm text-text-mid">
          {error instanceof Error && error.message ? error.message : "Something went wrong."} Your
          filters are kept in the address bar.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex min-h-11 items-center justify-center rounded-sm bg-accent-text px-4 text-sm font-semibold text-on-accent hover:opacity-90"
          >
            Retry
          </button>
          <a
            href="/"
            className="inline-flex min-h-11 items-center justify-center rounded-sm border border-border px-4 text-sm font-semibold text-text-hi hover:bg-bg-hover"
          >
            Command centre
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
      { title: "NIDAN — Track-circuit failure advisory" },
      {
        name: "description",
        content:
          "Advisory, non-vital failure propagation engine for Indian Railways track circuits.",
      },
      { name: "author", content: "NIDAN" },
      { property: "og:title", content: "NIDAN — Track-circuit failure advisory" },
      {
        property: "og:description",
        content:
          "Advisory, non-vital failure propagation engine for Indian Railways track circuits.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      // Fonts are self-hosted from /fonts (see src/styles/fonts.css); no CDN preconnect.
      {
        rel: "preload",
        href: "/fonts/Inter.woff2",
        as: "font",
        type: "font/woff2",
        crossOrigin: "anonymous",
      },
      {
        rel: "preload",
        href: "/fonts/NotoSansDevanagari.woff2",
        as: "font",
        type: "font/woff2",
        crossOrigin: "anonymous",
      },
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  // Shell counts (rail, tab bar) are server-rendered, so their data is loaded for every route.
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.ensureQueryData(alertsQuery),
      context.queryClient.ensureQueryData(clustersQuery),
    ]),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Applies the saved/system theme before first paint, so there is no flash. */}
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function useGlobalKeys() {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        !!target &&
        (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        useUi.getState().setPaletteOpen(!useUi.getState().paletteOpen);
        return;
      }
      if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey) {
        const local = document.querySelector<HTMLInputElement>("[data-page-search]");
        event.preventDefault();
        if (local) local.focus();
        else useUi.getState().setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const theme = useTheme();
  const lang = useUi((s) => s.lang);
  const isField = pathname === "/field" || pathname.startsWith("/field/");
  useGlobalKeys();

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(LANG_STORAGE_KEY);
      if (saved === "hi" || saved === "en") useUi.getState().setLang(saved);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === "hi" ? "hi" : "en";
  }, [lang]);

  return (
    <QueryClientProvider client={queryClient}>
      {isField ? (
        <Outlet />
      ) : (
        <ControlShell>
          <Outlet />
        </ControlShell>
      )}
      <Toaster
        theme={isField ? "light" : theme === "day" ? "light" : "dark"}
        position="bottom-right"
        offset={{ bottom: 72, right: 16 }}
        toastOptions={{
          classNames: {
            toast:
              "rounded-md! border! border-border-strong! bg-bg-panel! text-text-hi! shadow-float!",
            description: "text-text-mid!",
          },
        }}
      />
    </QueryClientProvider>
  );
}
