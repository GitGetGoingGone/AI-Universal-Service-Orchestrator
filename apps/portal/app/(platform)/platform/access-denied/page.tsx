import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function PlatformAccessDeniedPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[rgb(var(--color-background))] px-4">
      <div className="max-w-md text-center space-y-6">
        <h1 className="text-2xl font-bold text-amber-600 dark:text-amber-400">
          Access Denied
        </h1>
        <p className="text-[rgb(var(--color-text-secondary))]">
          You don&apos;t have permission to access the platform admin. This area is restricted to
          authorized platform administrators.
        </p>
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          If you believe you should have access, contact your platform administrator.
        </p>
        <div className="flex gap-4 justify-center">
          <Button variant="outline" asChild>
            <Link href="/">Return to Home</Link>
          </Button>
          <Button asChild>
            <Link href="/platform/login">Sign out & try different account</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
