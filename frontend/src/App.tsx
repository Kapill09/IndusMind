import { useEffect, useMemo, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorBoundary } from "@/components/feedback/error-boundary";
import { ToastProvider } from "@/components/feedback/toast";
import { useLocalDocuments } from "@/hooks/use-local-documents";
import { AnalyticsPage } from "@/pages/analytics";
import { AssistantPage } from "@/pages/assistant";
import { DashboardPage } from "@/pages/dashboard";
import { DocumentsPage } from "@/pages/documents";
import { SettingsPage } from "@/pages/settings";
import { UploadPage } from "@/pages/upload";
import type { ChatMessage, PageKey } from "@/types";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <IndusMindApp />
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

function IndusMindApp() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [questionsAsked, setQuestionsAsked] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("indus-mind-theme") === "dark");
  const { documents, totals, addUploadedDocument } = useLocalDocuments();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("indus-mind-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const page = useMemo(() => {
    switch (activePage) {
      case "assistant":
        return (
          <AssistantPage
            messages={messages}
            setMessages={setMessages}
            onQuestionAnswered={() => setQuestionsAsked((count) => count + 1)}
          />
        );
      case "upload":
        return <UploadPage onUploaded={addUploadedDocument} />;
      case "documents":
        return (
          <DocumentsPage
            documents={documents}
            onNavigate={setActivePage}
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
          />
        );
      case "analytics":
        return <AnalyticsPage totals={totals} questionsAsked={questionsAsked} />;
      case "settings":
        return <SettingsPage />;
      case "dashboard":
      default:
        return <DashboardPage documents={documents} totals={totals} questionsAsked={questionsAsked} />;
    }
  }, [activePage, addUploadedDocument, documents, messages, questionsAsked, searchQuery, totals]);

  return (
    <AppShell
      activePage={activePage}
      onNavigate={setActivePage}
      sidebarOpen={sidebarOpen}
      setSidebarOpen={setSidebarOpen}
      darkMode={darkMode}
      setDarkMode={setDarkMode}
      searchQuery={searchQuery}
      onSearchQueryChange={setSearchQuery}
    >
      {page}
    </AppShell>
  );
}
