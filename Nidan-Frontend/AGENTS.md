<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.

## What Lovable manages

Rules outside this block are the project's own. Change the pieces below in
Lovable, not by hand. With the [Lovable MCP](https://mcp.lovable.dev)
connected, `send_message` asks Lovable to do it; otherwise ask the user to
use the editor.

- **Database.** Do not add or edit `supabase/migrations/` or `drizzle/`.
  Ask Lovable to change the schema.
- **Generated files.** Do not edit a file whose header says it is automatically
  generated.
- **AI gateway.** Keep model calls on Lovable's gateway, and keep
  `LOVABLE_API_KEY` out of browser code.
- **Connectors.** Lovable provides native connectors. `list_connectors` shows
  which are enabled; `add_connector` only returns the dashboard link. When a
  connector is enabled, calls go through the connector gateway and need
  `LOVABLE_API_KEY`. When Lovable does not provide one, users can bring their
  own key and store it in Secrets.
- **Secrets.** Lovable manages them. Do not put secret values in the repo.
<!-- LOVABLE:END -->

## Application architecture

- Keep the UI in TanStack Start file routes; `__root.tsx` picks the Control shell or, for `/field*`, the Field shell, so the platform router and SSR entry stay intact.
- All data flows through the adapter in `src/lib/api.ts` (mock fixtures or `/v1` API via `VITE_DATA_SOURCE`) and TanStack Query options in `src/lib/queries.ts`; components never fetch, so the backend can be wired without touching screens.
- Query cache is dehydrated with `@tanstack/react-router-ssr-query`, and the root loader preloads shell counts, so SSR and hydration render identical markup.
- Colours come only from semantic tokens in `src/styles/tokens.css` (Day/Night via `data-theme`, field via `.field-surface`); base and component CSS sit in `@layer base/components` so Tailwind utilities always win.
- Ranking, levels and cluster membership are server outputs; the browser only sorts by `policyRank` and enforces workflow rules in `src/lib/policy.ts` (covered by `src/test/policy.test.ts`).
- The API surface and UI must never gain an interlocking/signal/route/points command; `src/test/safety.test.ts` guards this.

