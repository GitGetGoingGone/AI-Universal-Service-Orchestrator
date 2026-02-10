import Link from "next/link";
import { auth, currentUser } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { RegisterForm } from "./register-form";

export default async function RegisterPage() {
  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-up"); // afterSignUpUrl=/register on sign-up page
  }

  const user = await currentUser();
  const userEmail = user?.emailAddresses?.[0]?.emailAddress ?? null;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[rgb(var(--color-background))] px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Partner Registration</h1>
          <p className="mt-2 text-[rgb(var(--color-text-secondary))]">
            Apply to join USO as a partner. Platform admin will review your application.
          </p>
        </div>

        <RegisterForm userEmail={userEmail} />

        <p className="text-center text-sm text-[rgb(var(--color-text-secondary))]">
          Already have an account?{" "}
          <Link href="/sign-in" className="text-[rgb(var(--color-primary))] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
