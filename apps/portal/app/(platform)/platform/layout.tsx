import { PlatformLayoutClient } from "./platform-layout-client";

export default function PlatformSectionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <PlatformLayoutClient>{children}</PlatformLayoutClient>;
}
