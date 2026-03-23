"use client";

import { useState } from "react";
import { Button, Card, Chip, Separator } from "@heroui/react";
import DashboardTab from "./tabs/DashboardTab";
import PlanificacionesTab from "./tabs/PlanificacionesTab";
import AlumnosTab from "./tabs/AlumnosTab";
import AsistenteTab from "./tabs/AsistenteTab";
import CurricularSelector from "./CurricularSelector";

export type Tab = "dashboard" | "planificaciones" | "alumnos" | "asistente" | "programa";

const NAV: { id: Tab; label: string; icon: React.ReactNode }[] = [
  {
    id: "dashboard",
    label: "Inicio",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    id: "planificaciones",
    label: "Planificaciones",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
  {
    id: "alumnos",
    label: "Alumnos",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    id: "asistente",
    label: "Asistente",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    id: "programa",
    label: "Programa",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
    ),
  },
];

export default function AppShell() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  return (
    <div className="flex h-screen bg-background overflow-hidden">

      {/* ── Sidebar desktop ─────────────────────────────────────────────── */}
      <aside className="hidden md:flex flex-col w-56 border-r border-border bg-[var(--surface)] flex-shrink-0">
        {/* Logo */}
        <div className="px-4 py-5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center flex-shrink-0">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-foreground leading-none">Facilitador</p>
              <p className="text-xs text-muted-foreground leading-none mt-0.5">Docente EBI</p>
            </div>
          </div>
        </div>

        <Separator />

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={[
                  "w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm font-medium transition-all",
                  isActive
                    ? "bg-accent/10 text-accent"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                ].join(" ")}
              >
                <span className={isActive ? "text-accent" : ""}>{item.icon}</span>
                {item.label}
              </button>
            );
          })}
        </nav>

        <Separator />
        <div className="px-4 py-3">
          <Chip variant="soft" color="default" size="sm" className="w-full justify-center">
            Beta v0.1
          </Chip>
        </div>
      </aside>

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Mobile top bar */}
        <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-border bg-[var(--surface)]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={2.5}>
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
            </div>
            <span className="text-sm font-bold">Facilitador EBI</span>
          </div>
          <Chip variant="soft" size="sm">Beta v0.1</Chip>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "dashboard"      && <DashboardTab onNavigate={(t) => setActiveTab(t as Tab)} />}
          {activeTab === "planificaciones" && <PlanificacionesTab />}
          {activeTab === "alumnos"         && <AlumnosTab />}
          {activeTab === "asistente"       && (
            <div className="flex flex-col" style={{ height: "100%" }}>
              <AsistenteTab />
            </div>
          )}
          {activeTab === "programa" && (
            <div className="p-6 max-w-5xl w-full mx-auto">
              <div className="mb-6">
                <h2 className="text-xl font-bold text-foreground">Explorador del Programa EBI</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Navegá la estructura curricular: ciclos, espacios, unidades, contenidos, competencias y criterios de logro.
                </p>
              </div>
              <Card>
                <Card.Content className="p-6">
                  <CurricularSelector />
                </Card.Content>
              </Card>
            </div>
          )}
        </div>

        {/* Mobile bottom nav */}
        <div className="md:hidden flex border-t border-border bg-[var(--surface)]">
          {NAV.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={[
                  "flex-1 flex flex-col items-center gap-1 py-2.5 transition-colors text-xs font-medium",
                  isActive ? "text-accent" : "text-muted-foreground",
                ].join(" ")}
              >
                {item.icon}
                {item.label}
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}

