import type { ReactNode } from "react";

export interface TabDef {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: TabDef[];
  active: string;
  onChange: (id: string) => void;
}

export function Tabs({ tabs, active, onChange }: TabsProps) {
  const activeTab = tabs.find((t) => t.id === active) ?? tabs[0];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #e5e7eb",
          background: "#f9fafb",
          flexShrink: 0,
        }}
      >
        {tabs.map((t) => {
          const isActive = t.id === active;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onChange(t.id)}
              style={{
                flex: 1,
                padding: "8px 6px",
                fontSize: 12,
                fontWeight: isActive ? 600 : 400,
                background: isActive ? "#fff" : "transparent",
                color: isActive ? "#111827" : "#6b7280",
                border: "none",
                borderBottom: isActive ? "2px solid #2563eb" : "2px solid transparent",
                cursor: "pointer",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 12, minHeight: 0 }}>
        {activeTab?.content}
      </div>
    </div>
  );
}
