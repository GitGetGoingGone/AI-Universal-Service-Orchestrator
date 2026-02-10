import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function RegisterSuccessPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[rgb(var(--color-background))] px-4">
      <div className="max-w-md text-center space-y-6">
        <h1 className="text-2xl font-bold text-[rgb(var(--color-success))]">
          Application Submitted
        </h1>
        <p className="text-[rgb(var(--color-text-secondary))]">
          Your partner application has been received. A platform administrator will review it and contact you once approved.
        </p>
        <Button asChild>
          <Link href="/">Return to Home</Link>
        </Button>
      </div>
    </div>
  );
}
