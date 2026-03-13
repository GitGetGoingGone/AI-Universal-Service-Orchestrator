import { ConversationSidebar } from "./conversation-sidebar";

export default function ConversationsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[calc(100vh-0px)] min-h-0">
      <ConversationSidebar />
      <main className="flex-1 min-w-0 overflow-hidden flex flex-col" role="main">
        {children}
      </main>
    </div>
  );
}
