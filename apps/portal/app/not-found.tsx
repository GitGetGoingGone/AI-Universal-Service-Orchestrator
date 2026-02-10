import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[rgb(var(--color-background))] px-4">
      <h1 className="text-2xl font-bold">404</h1>
      <p className="mt-2 text-[rgb(var(--color-text-secondary))]">Page not found</p>
      <Button asChild className="mt-6">
        <Link href="/">Go home</Link>
      </Button>
    </div>
  );
}
