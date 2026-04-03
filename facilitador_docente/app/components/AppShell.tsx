"use client";

import React, { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { UserButton } from "@clerk/nextjs";
import { Button, Card, Chip, Separator } from "@heroui/react";
import {
  LayoutDashboard,
  FileText,
  Users,
  MessageSquare,
  BookOpen,
  Sun,
  Moon,
  type IconNode,
} from "lucide";
import DashboardTab from "./tabs/DashboardTab";
import PlanificacionesTab from "./tabs/PlanificacionesTab";
import AlumnosTab from "./tabs/AlumnosTab";
import AsistenteTab from "./tabs/AsistenteTab";
import ProgramaTab from "./tabs/ProgramaTab";

export type Tab = "dashboard" | "planificaciones" | "alumnos" | "asistente" | "programa";

type IconProps = { icon: IconNode; size?: number; stroke?: string; strokeWidth?: number };

function Icon({ icon, size = 16, stroke = "currentColor", strokeWidth = 2 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {icon.map(([tag, attrs], i) => {
        const El = tag as keyof React.JSX.IntrinsicElements;
        return <El key={i} {...(attrs as object)} />;
      })}
    </svg>
  );
}

const NAV: { id: Tab; label: string; icon: IconNode }[] = [
  { id: "dashboard",       label: "Inicio",          icon: LayoutDashboard },
  { id: "planificaciones", label: "Planificaciones",  icon: FileText        },
  { id: "alumnos",         label: "Alumnos",          icon: Users           },
  { id: "asistente",       label: "Asistente",        icon: MessageSquare   },
  { id: "programa",        label: "Programa",         icon: BookOpen        },
];

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) return <div className="w-[27px] h-[27px]" />;

  return (
    <button
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      aria-label="Cambiar tema"
    >
      <Icon icon={resolvedTheme === "dark" ? Sun : Moon} size={15} />
    </button>
  );
}

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
              <Icon icon={BookOpen} size={16} stroke="white" strokeWidth={2.5} />
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
                <Icon icon={item.icon} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <Separator />
        <div className="px-4 py-3 flex items-center justify-between">
          <Chip variant="soft" color="default" size="sm">
            Beta v0.1
          </Chip>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <UserButton afterSignOutUrl="/sign-in" />
          </div>
        </div>
      </aside>

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Mobile top bar */}
        <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-border bg-[var(--surface)]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
              <Icon icon={BookOpen} size={13} stroke="white" strokeWidth={2.5} />
            </div>
            <span className="text-sm font-bold">Facilitador EBI</span>
          </div>
          <div className="flex items-center gap-2">
            <Chip variant="soft" size="sm">Beta v0.1</Chip>
            <ThemeToggle />
            <UserButton afterSignOutUrl="/sign-in" />
          </div>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "dashboard"       && <DashboardTab onNavigate={(t) => setActiveTab(t as Tab)} />}
          {activeTab === "planificaciones" && <PlanificacionesTab />}
          {activeTab === "alumnos"         && <AlumnosTab />}
          {activeTab === "asistente"       && (
            <div className="flex flex-col" style={{ height: "100%" }}>
              <AsistenteTab />
            </div>
          )}
          {activeTab === "programa" && <ProgramaTab />}
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
                <Icon icon={item.icon} />
                {item.label}
              </button>
            );
          })}
        </div>
      </main>
    </div>
  );
}
