import { ConversationSidebar } from "./conversation-sidebar";

export default function ConversationsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[calc(100vh-8rem)]">
      <ConversationSidebar />
      <main className="flex-1 overflow-hidden flex flex-col">{children}</main>
    </div>
  );
}
