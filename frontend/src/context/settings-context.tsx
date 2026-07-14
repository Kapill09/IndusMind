import React, { createContext, useContext, useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";
export type SearchType = "hybrid" | "semantic" | "keyword";

export interface SettingsState {
  // Workspace
  workspaceName: string;
  theme: Theme;
  language: string;
  timezone: string;
  notificationsEnabled: boolean;
  autoSave: boolean;

  // AI Preferences
  aiModel: string;
  temperature: number;
  maxSources: number;
  topK: number;
  answerLength: "concise" | "detailed" | "comprehensive";
  citationStyle: "inline" | "footnotes" | "none";
  groundResponses: boolean;
  showConfidenceScore: boolean;
  autoExpandSources: boolean;
  enableContextVisualization: boolean;

  // Retrieval Settings
  searchType: SearchType;
  confidenceThreshold: number;
  autoMetadataFiltering: boolean;
  searchScope: "entire" | "selected";

  // Document Processing
  autoIndexUploads: boolean;
  generateKnowledgeGraph: boolean;
  extractEntities: boolean;
  ocrEnabled: boolean;
  duplicateDetection: boolean;
  versioning: boolean;
  autoSummaries: boolean;
}

export interface SettingsContextType extends SettingsState {
  updateSetting: <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => void;
  resetSettings: () => void;
}

const defaultSettings: SettingsState = {
  // Workspace
  workspaceName: "ET AI Hackathon",
  theme: "system",
  language: "English (US)",
  timezone: "UTC",
  notificationsEnabled: true,
  autoSave: true,

  // AI Preferences
  aiModel: "Gemini 3.1 Pro (High)",
  temperature: 0.7,
  maxSources: 5,
  topK: 10,
  answerLength: "detailed",
  citationStyle: "inline",
  groundResponses: true,
  showConfidenceScore: true,
  autoExpandSources: false,
  enableContextVisualization: true,

  // Retrieval Settings
  searchType: "hybrid",
  confidenceThreshold: 0.75,
  autoMetadataFiltering: true,
  searchScope: "entire",

  // Document Processing
  autoIndexUploads: true,
  generateKnowledgeGraph: true,
  extractEntities: true,
  ocrEnabled: false,
  duplicateDetection: true,
  versioning: false,
  autoSummaries: true,
};

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<SettingsState>(() => {
    try {
      const stored = localStorage.getItem("indus-mind-settings");
      if (stored) {
        return { ...defaultSettings, ...JSON.parse(stored) };
      }
    } catch (e) {
      console.error("Failed to parse settings from local storage", e);
    }
    return defaultSettings;
  });

  useEffect(() => {
    localStorage.setItem("indus-mind-settings", JSON.stringify(settings));
    
    // Apply theme
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    
    if (settings.theme === "system") {
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      root.classList.add(systemTheme);
    } else {
      root.classList.add(settings.theme);
    }
  }, [settings]);

  const updateSetting = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const resetSettings = () => {
    setSettings(defaultSettings);
  };

  return (
    <SettingsContext.Provider value={{ ...settings, updateSetting, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error("useSettings must be used within a SettingsProvider");
  }
  return context;
}
