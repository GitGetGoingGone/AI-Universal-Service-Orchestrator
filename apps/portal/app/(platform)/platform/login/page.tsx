import { SignIn } from "@clerk/nextjs";

export default function PlatformLoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[rgb(var(--color-background))]">
      <SignIn
        routing="path"
        path="/platform/login"
        signUpUrl="/sign-up"
        afterSignInUrl="/platform"
      />
    </div>
  );
}
