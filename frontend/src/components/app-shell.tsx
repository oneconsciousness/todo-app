import type { ReactNode } from "react";
import { routes } from "../lib/routes.ts";
import { Button } from "./ui/button.tsx";
import { LedgerTitle } from "./ui/ledger-title.tsx";
import { Link } from "./ui/link.tsx";

/** The signed-in account the masthead names, with its sign-out action. */
export interface ShellAccount {
  readonly email: string;
  readonly signingOut: boolean;
  readonly onSignOut: () => void;
}

/** Props for `AppShell`. */
export interface AppShellProps {
  /** The signed-in account, or null on a page a signed-out visitor can reach. */
  readonly account: ShellAccount | null;
  readonly children: ReactNode;
}

/** The frame around every signed-in screen: a binding band with the ledger's title, and the desk the page lies on. */
export function AppShell({ account, children }: AppShellProps) {
  return (
    <div className="@container">
      <header className="binding">
        <div className="mx-auto flex max-w-measure items-center justify-between gap-4 px-4 py-3 @wide:px-0">
          <Link href={routes.tasks} className="rounded-control">
            <LedgerTitle size="band" />
          </Link>
          {account && (
            <div className="flex min-w-0 items-center gap-4">
              <span className="hidden truncate text-caption @wide:block">{account.email}</span>
              <Button variant="binding" disabled={account.signingOut} onClick={account.onSignOut}>
                Sign out
              </Button>
            </div>
          )}
        </div>
      </header>
      <main className="px-2 py-4 @wide:px-12 @wide:py-12">{children}</main>
    </div>
  );
}
