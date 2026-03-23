"use client";

import { useEffect, useState } from "react";
import {
  Button, Card, Chip, Spinner,
  TextField, Label, Input, TextArea, FieldError,
  Select, ListBox,
} from "@heroui/react";
import {
  getPlanificaciones, getPlanificacion, createPlanificacion, deletePlanificacion,
  type Planificacion,
} from "../../api-actions";

type View = "list" | "create" | "detail";

const NIVELES = [
  "Inicial - Nivel 3", "Inicial - Nivel 4", "Inicial - Nivel 5",
  "1.er grado", "2.do grado", "3.er grado",
  "4.to grado", "5.to grado", "6.to grado",
];

export default function PlanificacionesTab() {
  const [view, setView] = useState<View>("list");
  const [plans, setPlans] = useState<Planificacion[]>([]);
  const [selected, setSelected] = useState<Planificacion | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(false);

  const reload = () => {
    setLoading(true);
    setApiError(false);
    getPlanificaciones()
      .then((p) => { setPlans(p); setLoading(false); })
      .catch(() => { setApiError(true); setLoading(false); });
  };

  useEffect(() => { reload(); }, []);

  const openDetail = async (id: number) => {
    const p = await getPlanificacion(id);
    if (p) { setSelected(p); setView("detail"); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar esta planificación? Esta acción no se puede deshacer.")) return;
    await deletePlanificacion(id);
    setView("list");
    reload();
  };

  if (view === "create") {
    return <CreateForm onBack={() => setView("list")} onSaved={() => { setView("list"); reload(); }} />;
  }
  if (view === "detail" && selected) {
    return <DetailView plan={selected} onBack={() => setView("list")} onDelete={() => handleDelete(selected.id)} />;
  }

  return (
    <div className="p-6 max-w-4xl w-full mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">Mis Planificaciones</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {loading ? "Cargando…" : `${plans.length} planificación${plans.length !== 1 ? "es" : ""}`}
          </p>
        </div>
        <Button variant="primary" size="sm" onPress={() => setView("create")}>
          <PlusIcon /> Nueva
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner color="accent" /></div>
      ) : apiError ? (
        <Card variant="transparent" className="border border-dashed border-danger/40 p-10 flex flex-col items-center gap-4 text-center">
          <p className="text-sm text-danger">No se pudo conectar con la API.</p>
          <Button variant="danger" size="sm" onPress={reload}>Reintentar</Button>
        </Card>
      ) : plans.length === 0 ? (
        <Card variant="transparent" className="border border-dashed border-border p-12 flex flex-col items-center gap-4 text-center">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center text-accent">
            <DocIcon size={28} />
          </div>
          <div>
            <p className="font-semibold text-foreground">No hay planificaciones aún</p>
            <p className="text-sm text-muted-foreground mt-1">Creá tu primera planificación para comenzar.</p>
          </div>
          <Button variant="primary" onPress={() => setView("create")}>+ Nueva planificación</Button>
        </Card>
      ) : (
        <div className="space-y-2">
          {plans.map((p) => (
            <Card
              key={p.id}
              variant="default"
              className="cursor-pointer hover:shadow-md transition-shadow"
            >
              <button onClick={() => openDetail(p.id)} className="w-full flex items-center gap-4 p-4 text-left">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent flex-shrink-0">
                  <DocIcon />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground text-sm truncate">{p.nombre}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {[p.nivel, p.periodo_inicio ? `${p.periodo_inicio}${p.periodo_fin ? ` → ${p.periodo_fin}` : ""}` : undefined]
                      .filter(Boolean).join(" · ")}
                  </p>
                  {p.descripcion && (
                    <p className="text-xs text-muted-foreground/70 mt-0.5 truncate">{p.descripcion}</p>
                  )}
                </div>
                <svg className="w-4 h-4 text-muted-foreground flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Detail ────────────────────────────────────────────────────────────────────

function DetailView({ plan, onBack, onDelete }: { plan: Planificacion; onBack: () => void; onDelete: () => void }) {
  return (
    <div className="p-6 max-w-3xl w-full mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" isIconOnly size="sm" onPress={onBack}>
          <BackIcon />
        </Button>
        <h2 className="text-xl font-bold text-foreground flex-1 truncate">{plan.nombre}</h2>
        <Button variant="danger" size="sm" onPress={onDelete}>
          <TrashIcon /> Eliminar
        </Button>
      </div>

      <div className="space-y-3">
        {plan.nivel && (
          <Card variant="secondary" className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Nivel educativo</p>
            <p className="text-sm text-foreground">{plan.nivel}</p>
          </Card>
        )}
        {plan.descripcion && (
          <Card variant="secondary" className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Descripción</p>
            <p className="text-sm text-foreground">{plan.descripcion}</p>
          </Card>
        )}
        {plan.periodo_inicio && (
          <Card variant="secondary" className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Período</p>
            <p className="text-sm text-foreground">
              {plan.periodo_inicio}{plan.periodo_fin ? ` → ${plan.periodo_fin}` : ""}
            </p>
          </Card>
        )}
        {plan.chat_exportado && (
          <Card variant="secondary" className="p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Planificación generada por el agente
            </p>
            <pre className="text-sm text-foreground whitespace-pre-wrap font-mono leading-relaxed bg-background rounded-lg p-3 overflow-auto">
              {plan.chat_exportado}
            </pre>
          </Card>
        )}
      </div>
    </div>
  );
}

// ── Create form ───────────────────────────────────────────────────────────────

function CreateForm({ onBack, onSaved }: { onBack: () => void; onSaved: () => void }) {
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [nivel, setNivel] = useState<string>("");
  const [inicio, setInicio] = useState("");
  const [fin, setFin] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [touched, setTouched] = useState(false);

  const save = async () => {
    setTouched(true);
    if (!nombre.trim()) { setError(""); return; }
    setSaving(true);
    const result = await createPlanificacion({
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || undefined,
      nivel: nivel || undefined,
      periodo_inicio: inicio.trim() || undefined,
      periodo_fin: fin.trim() || undefined,
    });
    setSaving(false);
    if (result) onSaved();
    else setError("Error al guardar. Verificá que la API esté activa.");
  };

  return (
    <div className="p-6 max-w-2xl w-full mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" isIconOnly size="sm" onPress={onBack}>
          <BackIcon />
        </Button>
        <h2 className="text-xl font-bold text-foreground">Nueva Planificación</h2>
      </div>

      <div className="space-y-4">
        <TextField
          fullWidth
          isRequired
          isInvalid={touched && !nombre.trim()}
          value={nombre}
          onChange={setNombre}
        >
          <Label>Nombre</Label>
          <Input placeholder="Ej: Planificación Matemática – Tramo 2" />
          {touched && !nombre.trim() && <FieldError>El nombre es requerido.</FieldError>}
        </TextField>

        <TextField fullWidth value={descripcion} onChange={setDescripcion}>
          <Label>Descripción</Label>
          <TextArea placeholder="Descripción breve de la planificación..." rows={3} />
        </TextField>

        <Select
          fullWidth
          placeholder="Seleccionar nivel"
          value={nivel || null}
          onChange={(key) => setNivel(String(key ?? ""))}
        >
          <Label>Nivel educativo</Label>
          <Select.Trigger>
            <Select.Value />
            <Select.Indicator />
          </Select.Trigger>
          <Select.Popover>
            <ListBox>
              {NIVELES.map((n) => (
                <ListBox.Item key={n} id={n} textValue={n}>
                  {n}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>

        <div className="grid grid-cols-2 gap-4">
          <TextField fullWidth value={inicio} onChange={setInicio}>
            <Label>Período inicio</Label>
            <Input placeholder="Ej: Marzo 2025" />
          </TextField>
          <TextField fullWidth value={fin} onChange={setFin}>
            <Label>Período fin</Label>
            <Input placeholder="Ej: Junio 2025" />
          </TextField>
        </div>

        {error && (
          <Chip color="danger" variant="soft" className="w-full justify-start px-3 py-2 text-sm rounded-xl h-auto">
            {error}
          </Chip>
        )}

        <div className="flex gap-3 pt-2">
          <Button variant="tertiary" fullWidth onPress={onBack}>Cancelar</Button>
          <Button variant="primary" fullWidth isPending={saving} onPress={save}>
            {({ isPending }) => isPending ? <><Spinner size="sm" color="current" /> Guardando…</> : "Guardar Planificación"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Iconos ────────────────────────────────────────────────────────────────────
function DocIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}
function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}
function BackIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 19l-7-7 7-7" />
    </svg>
  );
}
function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}
