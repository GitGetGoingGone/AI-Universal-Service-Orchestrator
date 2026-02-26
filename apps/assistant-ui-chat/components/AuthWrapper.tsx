"use client";

import { createContext, useContext, type ReactNode } from "react";
import { SignInButton, SignOutButton, useUser } from "@clerk/nextjs";

export const hasClerk = !!(
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
);

type AuthState = { isSignedIn: boolean; userId: string | null };
const defaultAuth: AuthState = { isSignedIn: false, userId: null };
const AuthContext = createContext<AuthState>(defaultAuth);

export function useAuthState(): AuthState {
  return useContext(AuthContext);
}

function ClerkAuthProvider({ children }: { children: ReactNode }) {
  const { isSignedIn, user } = useUser();
  const userId = user?.id ?? null;
  return (
    <AuthContext.Provider value={{ isSignedIn: !!isSignedIn, userId }}>
      {children}
    </AuthContext.Provider>
  );
}

function NoAuthProvider({ children }: { children: ReactNode }) {
  return (
    <AuthContext.Provider value={defaultAuth}>{children}</AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  return hasClerk ? (
    <ClerkAuthProvider>{children}</ClerkAuthProvider>
  ) : (
    <NoAuthProvider>{children}</NoAuthProvider>
  );
}

export function AuthButtons() {
  if (!hasClerk) return null;
  return <AuthButtonsInner />;
}

function AuthButtonsInner() {
  const { isSignedIn, isLoaded } = useUser();
  const showSignOut = !!isLoaded && !!isSignedIn;
  return (
    <div className="flex items-center gap-3">
      {showSignOut ? (
        <SignOutButton>
          <button className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--border)]/50">
            Sign out
          </button>
        </SignOutButton>
      ) : (
        <SignInButton mode="modal">
          <button className="rounded-lg bg-[var(--primary)] px-3 py-1.5 text-sm text-[var(--primary-foreground)] hover:opacity-90">
            Sign in
          </button>
        </SignInButton>
      )}
    </div>
  );
}
