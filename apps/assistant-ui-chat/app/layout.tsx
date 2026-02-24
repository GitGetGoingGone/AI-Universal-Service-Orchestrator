import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Assistant UI Chat",
  description: "Chat UI powered by assistant-ui, connected to USO Gateway",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
