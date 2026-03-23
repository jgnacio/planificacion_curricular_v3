"use client";

import { useEffect, useState } from "react";
import {
  Button, Card, Avatar, Chip, Spinner,
  TextField, Label, Input, TextArea, FieldError,
  Select, ListBox,
} from "@heroui/react";
import { getAlumnos, createAlumno, type Alumno } from "../../api-actions";

const NIVELES = ["Inicial", "Primaria", "Secundaria"];
const GRADOS = [
  "Nivel 3 años", "Nivel 4 años", "Nivel 5 años",
  "1.er grado", "2.do grado", "3.er grado",
  "4.to grado", "5.to grado", "6.to grado",
];

const COLORS: Array<"default" | "accent" | "success" | "warning" | "danger"> = [
  "accent", "success", "warning", "danger",
];

function avatarColor(name: string): "default" | "accent" | "success" | "warning" | "danger" {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return COLORS[Math.abs(h) % COLORS.length];
}

type View = "list" | "create";

export default function AlumnosTab() {
  const [view, setView] = useState<View>("list");
  const [alumnos, setAlumnos] = useState<Alumno[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const reload = () => {
    setLoading(true);
    getAlumnos().then((a) => { setAlumnos(a); setLoading(false); });
  };

  useEffect(() => { reload(); }, []);

  const filtered = alumnos.filter((a) =>
    a.nombre_completo.toLowerCase().includes(search.toLowerCase())
  );

  if (view === "create") {
    return (
      <CreateForm
        onBack={() => setView("list")}
        onSaved={() => { setView("list"); reload(); }}
      />
    );
  }

  return (
    <div className="p-6 max-w-4xl w-full mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">Mis Alumnos</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {loading ? "Cargando…" : `${alumnos.length} alumno${alumnos.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <Button variant="primary" size="sm" onPress={() => setView("create")}>
          <PersonAddIcon /> Agregar
        </Button>
      </div>

      {/* Search */}
      {!loading && alumnos.length > 0 && (
        <TextField fullWidth className="mb-5" value={search} onChange={setSearch}>
          <Input placeholder="Buscar alumno por nombre…" />
        </TextField>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-16"><Spinner color="success" /></div>
      ) : alumnos.length === 0 ? (
        <Card variant="transparent" className="border border-dashed border-border p-12 flex flex-col items-center gap-4 text-center">
          <div className="w-14 h-14 rounded-2xl bg-success/10 flex items-center justify-center text-success">
            <GroupIcon size={28} />
          </div>
          <div>
            <p className="font-semibold text-foreground">No hay alumnos registrados</p>
            <p className="text-sm text-muted-foreground mt-1">Agregá tus alumnos para vincularlos a planificaciones.</p>
          </div>
          <Button variant="primary" onPress={() => setView("create")}>+ Agregar alumno</Button>
        </Card>
      ) : filtered.length === 0 ? (
        <p className="text-center text-muted-foreground py-8 text-sm">
          No se encontraron alumnos con &quot;{search}&quot;.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {filtered.map((a) => <AlumnoCard key={a.id} alumno={a} />)}
        </div>
      )}
    </div>
  );
}

// ── Alumno card ───────────────────────────────────────────────────────────────

function AlumnoCard({ alumno }: { alumno: Alumno }) {
  const sub = [alumno.nivel, alumno.grado].filter(Boolean).join(" · ");
  return (
    <Card variant="default" className="flex flex-row items-start gap-3 p-4">
      <Avatar size="md" color={avatarColor(alumno.nombre_completo)}>
        <Avatar.Fallback>{alumno.nombre_completo?.[0]?.toUpperCase() ?? "?"}</Avatar.Fallback>
      </Avatar>
      <div className="flex-1 min-w-0 mt-0.5">
        <p className="font-semibold text-foreground text-sm">{alumno.nombre_completo}</p>
        {sub && (
          <Chip variant="soft" color="default" size="sm" className="mt-1">
            {sub}
          </Chip>
        )}
        {alumno.notas && (
          <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">{alumno.notas}</p>
        )}
      </div>
    </Card>
  );
}

// ── Create form ───────────────────────────────────────────────────────────────

function CreateForm({ onBack, onSaved }: { onBack: () => void; onSaved: () => void }) {
  const [nombre, setNombre] = useState("");
  const [nacimiento, setNacimiento] = useState("");
  const [nivel, setNivel] = useState("");
  const [grado, setGrado] = useState("");
  const [notas, setNotas] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [touched, setTouched] = useState(false);

  const save = async () => {
    setTouched(true);
    if (!nombre.trim()) return;
    setSaving(true);
    const result = await createAlumno({
      nombre_completo: nombre.trim(),
      fecha_nacimiento: nacimiento.trim() || undefined,
      nivel: nivel || undefined,
      grado: grado || undefined,
      notas: notas.trim() || undefined,
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
        <h2 className="text-xl font-bold text-foreground">Nuevo Alumno</h2>
      </div>

      <div className="space-y-4">
        <TextField
          fullWidth
          isRequired
          isInvalid={touched && !nombre.trim()}
          value={nombre}
          onChange={setNombre}
        >
          <Label>Nombre completo</Label>
          <Input placeholder="Ej: Ana García" />
          {touched && !nombre.trim() && <FieldError>El nombre es requerido.</FieldError>}
        </TextField>

        <TextField fullWidth value={nacimiento} onChange={setNacimiento}>
          <Label>Fecha de nacimiento</Label>
          <Input placeholder="dd/mm/aaaa" />
        </TextField>

        <div className="grid grid-cols-2 gap-4">
          <Select
            fullWidth
            placeholder="Seleccionar"
            value={nivel || null}
            onChange={(key) => setNivel(String(key ?? ""))}
          >
            <Label>Nivel</Label>
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                {NIVELES.map((n) => (
                  <ListBox.Item key={n} id={n} textValue={n}>
                    {n}<ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>

          <Select
            fullWidth
            placeholder="Seleccionar"
            value={grado || null}
            onChange={(key) => setGrado(String(key ?? ""))}
          >
            <Label>Grado</Label>
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                {GRADOS.map((g) => (
                  <ListBox.Item key={g} id={g} textValue={g}>
                    {g}<ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>

        <TextField fullWidth value={notas} onChange={setNotas}>
          <Label>Singularidades / Notas</Label>
          <TextArea
            placeholder="Estilos de aprendizaje, necesidades educativas específicas, fortalezas, intereses..."
            rows={4}
          />
        </TextField>

        {error && (
          <Chip color="danger" variant="soft" className="w-full justify-start px-3 py-2 text-sm rounded-xl h-auto">
            {error}
          </Chip>
        )}

        <div className="flex gap-3 pt-2">
          <Button variant="tertiary" fullWidth onPress={onBack}>Cancelar</Button>
          <Button variant="primary" fullWidth isPending={saving} onPress={save}>
            {({ isPending }) => isPending ? <><Spinner size="sm" color="current" /> Guardando…</> : "Guardar Alumno"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Iconos ────────────────────────────────────────────────────────────────────
function GroupIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
function PersonAddIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
      <line x1="19" y1="8" x2="19" y2="14" /><line x1="22" y1="11" x2="16" y2="11" />
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
