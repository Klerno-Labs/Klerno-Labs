import { AccessTokenContext } from "@/access-token-context";
import { stackClientApp } from "@/lib/stack";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useContext, useMemo, useState } from "react";

function pickEnv(...vals: Array<string | undefined>): string | undefined {
    for (const v of vals) {
        if (typeof v !== "string") continue;
        let s = v.trim();
        if ((s.startsWith("\"") && s.endsWith("\"")) || (s.startsWith("'") && s.endsWith("'"))) {
            s = s.slice(1, -1);
        }
        if (!s || s.toUpperCase() === "REPLACE_ME") continue;
        return s;
    }
    return undefined;
}

const projectId = pickEnv(
    import.meta.env.VITE_PUBLIC_STACK_PROJECT_ID as string | undefined,
    import.meta.env.VITE_STACK_PROJECT_ID as string | undefined,
);
const publishableKey = pickEnv(
    import.meta.env.VITE_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY as string | undefined,
    import.meta.env.VITE_STACK_PUBLISHABLE_CLIENT_KEY as string | undefined,
);
const missingAuthEnv =
    !projectId || projectId === "REPLACE_ME" || !publishableKey || publishableKey === "REPLACE_ME";

export const Route = createFileRoute("/token")({
    component: TokenPage,
    // Require auth before accessing this page
    beforeLoad(ctx) {
        // If env isn't configured yet, allow the page to render a helpful message
        if (missingAuthEnv) return;
        if (!ctx.context.accessToken) {
            return stackClientApp.redirectToSignIn();
        }
    },
});

function b64urlToJson(part?: string): unknown {
    if (!part) return null;
    try {
        // Convert base64url to base64
        const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
        // atob expects proper padding
        const padded = base64 + "===".slice((base64.length + 3) % 4);
        const json = atob(padded);
        return JSON.parse(json);
    } catch {
        return null;
    }
}

function useDecodedJwt(token: string | null) {
    return useMemo(() => {
        if (!token || token.split(".").length !== 3) return { header: null, payload: null } as const;
        const [h, p] = token.split(".");
        return {
            header: b64urlToJson(h),
            payload: b64urlToJson(p),
        } as const;
    }, [token]);
}

function TokenPage() {
    const token = useContext(AccessTokenContext);
    const { header, payload } = useDecodedJwt(token);
    const [copied, setCopied] = useState(false);

    const expText = useMemo(() => {
        const exp = (payload as any)?.exp as number | undefined;
        if (!exp) return "unknown";
        const d = new Date(exp * 1000);
        return `${d.toLocaleString()} (${d.toISOString()})`;
    }, [payload]);

    async function copy() {
        if (!token) return;
        try {
            await navigator.clipboard.writeText(token);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        } catch {
            // ignore
        }
    }

    if (missingAuthEnv) {
        return (
            <div className="flex flex-col gap-4">
                <h3>Neon Auth not configured</h3>
                <p className="text-foreground/70">
                    To use this page, set your Neon Auth values in <code>.env</code> then restart the dev
                    server:
                </p>
                <pre className="p-3 rounded border border-foreground/20 bg-background/50 text-xs overflow-auto">
                    {`VITE_PUBLIC_STACK_PROJECT_ID=${projectId ?? "<missing>"}
    VITE_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=${publishableKey ?? "<missing>"}
    `}
                </pre>
                <ol className="list-decimal ml-6 text-sm text-foreground/80">
                    <li>
                        In Neon Console → Auth, copy Project ID and Publishable client key into
                        vendor/.env
                    </li>
                    <li>Stop and re-run the dev server (npm run dev)</li>
                    <li>Return here to copy your access token (JWT)</li>
                </ol>
                <Link to="/">Back to app</Link>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h3>Neon Auth Access Token</h3>
                <Link to="/">Back to app</Link>
            </div>
            <p className="text-foreground/70">
                This is your current signed-in access token (JWT) issued by Neon Auth. Use it as the
                Bearer token for Neon Data API and for the backend proxy&apos;s NEON_API_KEY.
            </p>
            <div className="flex gap-3 items-center">
                <button type="button" className="cursor-pointer" onClick={copy} disabled={!token}>
                    {copied ? "Copied ✓" : "Copy token"}
                </button>
                <span className="text-foreground/70 text-sm">exp: {expText}</span>
            </div>
            <label className="text-sm text-foreground/70">Token</label>
            <textarea
                readOnly
                value={token ?? ""}
                className="w-full h-40 p-3 rounded border border-foreground/20 bg-background/50 font-mono text-xs"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h4 className="mb-2">Header</h4>
                    <pre className="w-full p-3 rounded border border-foreground/20 bg-background/50 text-xs overflow-auto">
                        {header ? JSON.stringify(header, null, 2) : "<not available>"}
                    </pre>
                </div>
                <div>
                    <h4 className="mb-2">Payload</h4>
                    <pre className="w-full p-3 rounded border border-foreground/20 bg-background/50 text-xs overflow-auto">
                        {payload ? JSON.stringify(payload, null, 2) : "<not available>"}
                    </pre>
                </div>
            </div>
        </div>
    );
}
