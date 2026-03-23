"use client";

import { useEffect, useState } from "react";
import { Button, Card, Avatar, Chip, Spinner } from "@heroui/react";
import { getPlanificaciones, getAlumnos, type Planificacion, type Alumno } from "../../api-actions";

type Props = { onNavigate: (tab: string) => void };

const ESPACIOS = 7;

const AVATAR_COLORS: Array<"default" | "accent" | "success" | "warning" | "danger"> = [
  "accent", "success", "warning", "danger",
];

function avatarColor(name: string): "default" | "accent" | "success" | "warning" | "danger" {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
}

export default function DashboardTab({ onNavigate }: Props) {
  const [planificaciones, setPlanificaciones] = useState<Planificacion[]>([]);
  const [alumnos, setAlumnos] = useState<Alumno[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    Promise.all([getPlanificaciones(), getAlumnos()]).then(([p, a]) => {
      setPlanificaciones(p);
      setAlumnos(a);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, []);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Buenos días";
    if (h < 20) return "Buenas tardes";
    return "Buenas noches";
  };

  const formattedDate = () => {
    const now = new Date();
    const days = ["domingo","lunes","martes","miércoles","jueves","viernes","sábado"];
    const months = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
    const d = days[now.getDay()];
    return `${d[0].toUpperCase()}${d.slice(1)}, ${now.getDate()} de ${months[now.getMonth()]}`;
  };

  const recent = planificaciones.slice(-4).reverse();

  return (
    <div className="flex flex-col min-h-full">

      {/* ── Hero header ──────────────────────────────────────────────────── */}
      <div className="px-8 py-8 text-white" style={{ background: "linear-gradient(135deg, oklch(0.42 0.185 253) 0%, oklch(0.32 0.18 253) 100%)" }}>
        <p className="text-sm font-medium opacity-75 mb-1">{greeting()}</p>
        <h1 className="text-2xl font-bold tracking-tight">Facilitador Docente EBI</h1>
        <p className="text-sm mt-1 opacity-60 flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          {formattedDate()}
        </p>
      </div>

      <div className="flex-1 p-6 space-y-8 max-w-5xl w-full mx-auto">

        {/* ── Stats ─────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-4">
          <StatCard
            icon={<DocIcon />}
            label="Planificaciones"
            value={loading ? "–" : String(planificaciones.length)}
            chipColor="accent"
          />
          <StatCard
            icon={<GroupIcon />}
            label="Alumnos"
            value={loading ? "–" : String(alumnos.length)}
            chipColor="success"
          />
          <StatCard
            icon={<BookIcon />}
            label="Espacios EBI"
            value={String(ESPACIOS)}
            chipColor="warning"
          />
        </div>

        {/* ── Planificaciones recientes ──────────────────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-foreground">Planificaciones recientes</h2>
            <Button variant="ghost" size="sm" onPress={() => onNavigate("planificaciones")}>
              Ver todas →
            </Button>
          </div>

          {loading ? (
            <div className="flex justify-center py-10">
              <Spinner color="accent" />
            </div>
          ) : recent.length === 0 ? (
            <EmptyCard
              icon={<DocIcon />}
              message="Todavía no hay planificaciones. Creá la primera."
              action={
                <Button variant="primary" size="sm" onPress={() => onNavigate("planificaciones")}>
                  + Nueva planificación
                </Button>
              }
            />
          ) : (
            <div className="space-y-2">
              {recent.map((p) => (
                <PlanRow key={p.id} plan={p} onClick={() => onNavigate("planificaciones")} />
              ))}
            </div>
          )}
        </section>

        {/* ── Acciones rápidas ──────────────────────────────────────────── */}
        <section>
          <h2 className="text-base font-bold text-foreground mb-4">Acciones rápidas</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <QuickAction
              icon={<AddIcon />}
              label="Nueva Planificación"
              chipColor="accent"
              onPress={() => onNavigate("planificaciones")}
            />
            <QuickAction
              icon={<PersonAddIcon />}
              label="Agregar Alumno"
              chipColor="success"
              onPress={() => onNavigate("alumnos")}
            />
            <QuickAction
              icon={<ChatIcon />}
              label="Asistente Docente"
              chipColor="danger"
              onPress={() => onNavigate("asistente")}
            />
            <QuickAction
              icon={<BookIcon />}
              label="Explorar Programa"
              chipColor="warning"
              onPress={() => onNavigate("programa")}
            />
          </div>
        </section>

        {/* ── Alumnos recientes ──────────────────────────────────────────── */}
        {!loading && alumnos.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-foreground">Alumnos registrados</h2>
              <Button variant="ghost" size="sm" onPress={() => onNavigate("alumnos")}>
                Ver todos →
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {alumnos.slice(0, 8).map((a) => (
                <Card key={a.id} variant="secondary" className="flex-row items-center gap-2 px-3 py-2">
                  <Avatar size="sm" color={avatarColor(a.nombre_completo)}>
                    <Avatar.Fallback>
                      {a.nombre_completo?.[0]?.toUpperCase() ?? "?"}
                    </Avatar.Fallback>
                  </Avatar>
                  <div>
                    <p className="text-sm font-medium text-foreground leading-none">{a.nombre_completo}</p>
                    {(a.nivel || a.grado) && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {[a.nivel, a.grado].filter(Boolean).join(" · ")}
                      </p>
                    )}
                  </div>
                </Card>
              ))}
              {alumnos.length > 8 && (
                <div className="flex items-center px-3 py-2 text-sm text-muted-foreground">
                  +{alumnos.length - 8} más
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

// ── Sub-componentes ───────────────────────────────────────────────────────────

type ChipColor = "default" | "accent" | "success" | "warning" | "danger";

function StatCard({ icon, label, value, chipColor }: { icon: React.ReactNode; label: string; value: string; chipColor: ChipColor }) {
  return (
    <Card variant="secondary" className="p-4 flex flex-col gap-3">
      <Chip variant="soft" color={chipColor} size="sm" className="w-fit">
        {icon}
        <Chip.Label>{label}</Chip.Label>
      </Chip>
      <p className="text-3xl font-extrabold text-foreground leading-none">{value}</p>
    </Card>
  );
}

function PlanRow({ plan, onClick }: { plan: Planificacion; onClick: () => void }) {
  const sub = [
    plan.nivel,
    plan.periodo_inicio ? `${plan.periodo_inicio}${plan.periodo_fin ? ` → ${plan.periodo_fin}` : ""}` : undefined,
  ].filter(Boolean).join(" · ");

  return (
    <Card variant="default" className="cursor-pointer hover:shadow-md transition-shadow">
      <button onClick={onClick} className="w-full flex items-center gap-4 p-4 text-left">
        <div className="w-9 h-9 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0 text-accent">
          <DocIcon />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-foreground text-sm truncate">{plan.nombre}</p>
          {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
        </div>
        <svg className="w-4 h-4 text-muted-foreground flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </Card>
  );
}

function QuickAction({ icon, label, chipColor, onPress }: { icon: React.ReactNode; label: string; chipColor: ChipColor; onPress: () => void }) {
  return (
    <Card variant="secondary" className="cursor-pointer hover:shadow-md transition-all">
      <button onMouseDown={onPress} className="w-full flex flex-col items-start gap-3 p-4 text-left">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center bg-${chipColor}/10 text-${chipColor}`}>
          {icon}
        </div>
        <p className="text-sm font-semibold text-foreground leading-tight">{label}</p>
      </button>
    </Card>
  );
}

function EmptyCard({ icon, message, action }: { icon: React.ReactNode; message: string; action?: React.ReactNode }) {
  return (
    <Card variant="transparent" className="border border-dashed border-border p-8 flex flex-col items-center gap-3 text-center">
      <div className="text-muted-foreground">{icon}</div>
      <p className="text-sm text-muted-foreground">{message}</p>
      {action}
    </Card>
  );
}

// ── Iconos ────────────────────────────────────────────────────────────────────
function DocIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}
function GroupIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
function BookIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  );
}
function AddIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" />
    </svg>
  );
}
function PersonAddIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
      <line x1="19" y1="8" x2="19" y2="14" /><line x1="22" y1="11" x2="16" y2="11" />
    </svg>
  );
}
function ChatIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
