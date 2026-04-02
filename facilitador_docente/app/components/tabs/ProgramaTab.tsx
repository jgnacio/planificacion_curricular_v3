"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { getCurriculumEstructura, type CurriculumEstructura } from "../../api-actions";

// ── Types ─────────────────────────────────────────────────────────────────────

type CE = { codigo: string; texto: string; mcn: string[] };
type ContenidoItem = {
  eje: string;
  contenido_estructurante: string;
  especificos: string[];
  competencias_relacionadas: string[];
};
type GradoContenidos = { label: string; items: ContenidoItem[] };
type GradoCriterios = { label: string; por_competencia: Record<string, string[]> };
type Materia = {
  nombre: string;
  competencias_especificas: CE[];
  contenidos: Record<string, GradoContenidos>;
  criterios: Record<string, GradoCriterios>;
};
type Espacio = { nombre: string; materias: Record<string, Materia> };
type Tramo = { label: string; espacios: Record<string, Espacio> };

type ActiveTab = "ces" | "contenidos" | "criterios";

const GRADE_LABELS: Record<string, string> = {
  "3er_grado": "3.er grado",
  "4to_grado": "4.to grado",
  "5to_grado": "5.to grado",
  "6to_grado": "6.to grado",
};

const TRAMO_GRADES: Record<string, string[]> = {
  tramo_3: ["3er_grado", "4to_grado"],
  tramo_4: ["5to_grado", "6to_grado"],
};

// ── Sub-components ────────────────────────────────────────────────────────────

function SelectorButton({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <button
      onClick={onPress}
      className={[
        "px-3 py-1.5 rounded-lg text-sm font-medium transition-all border",
        active
          ? "bg-accent/10 text-accent border-accent/30"
          : "text-muted-foreground border-border hover:bg-muted hover:text-foreground",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function TabButton({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <button
      onClick={onPress}
      className={[
        "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
        active
          ? "border-accent text-accent"
          : "border-transparent text-muted-foreground hover:text-foreground hover:border-border",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

// ── CE Accordion ──────────────────────────────────────────────────────────────

function CEAccordion({ ces }: { ces: CE[] }) {
  const [openCodes, setOpenCodes] = useState<Set<string>>(new Set());

  const toggle = (code: string) => {
    setOpenCodes((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  if (ces.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No hay competencias específicas registradas para esta materia.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {ces.map((ce) => {
        const isOpen = openCodes.has(ce.codigo);
        const preview = ce.texto.slice(0, 80) + (ce.texto.length > 80 ? "…" : "");
        return (
          <div key={ce.codigo} className="border border-border rounded-xl overflow-hidden">
            <button
              onClick={() => toggle(ce.codigo)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/40 transition-colors"
            >
              <Chip size="sm" className="bg-accent/10 text-accent flex-shrink-0">
                {ce.codigo}
              </Chip>
              <span className="text-sm text-foreground flex-1 min-w-0">
                {isOpen ? ce.texto.slice(0, 60) + "…" : preview}
              </span>
              <svg
                className={[
                  "w-4 h-4 text-muted-foreground flex-shrink-0 transition-transform",
                  isOpen ? "rotate-180" : "",
                ].join(" ")}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {isOpen && (
              <div className="px-4 pb-4 space-y-3 bg-muted/20">
                <p className="text-sm text-foreground leading-relaxed pt-2">{ce.texto}</p>
                {ce.mcn.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {ce.mcn.map((m) => (
                      <Chip key={m} size="sm" className="bg-success/10 text-success text-xs">
                        {m}
                      </Chip>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Contenidos panel ──────────────────────────────────────────────────────────

function ContenidosPanel({
  gradoData,
}: {
  gradoData: GradoContenidos | undefined;
}) {
  if (!gradoData) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No hay contenidos registrados para este grado.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {gradoData.items.map((item, idx) => (
        <div key={idx} className="border border-border rounded-xl p-4 space-y-2">
          {item.eje && (
            <p className="text-xs font-semibold uppercase tracking-wide text-accent">
              {item.eje}
            </p>
          )}
          <p className="text-sm font-semibold text-foreground">
            {item.contenido_estructurante}
          </p>
          {item.especificos.length > 0 && (
            <ul className="list-disc list-inside space-y-0.5 pl-1">
              {item.especificos.map((esp, i) => (
                <li key={i} className="text-sm text-muted-foreground leading-relaxed">
                  {esp}
                </li>
              ))}
            </ul>
          )}
          {item.competencias_relacionadas.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {item.competencias_relacionadas.map((ce) => (
                <Chip key={ce} size="sm" className="bg-accent/10 text-accent">
                  {ce}
                </Chip>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Criterios panel ───────────────────────────────────────────────────────────

function CriteriosPanel({
  gradoData,
  ces,
}: {
  gradoData: GradoCriterios | undefined;
  ces: CE[];
}) {
  if (!gradoData) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No hay criterios registrados para este grado.
      </p>
    );
  }

  const ceMap = Object.fromEntries(ces.map((c) => [c.codigo, c.texto]));

  return (
    <div className="space-y-4">
      {Object.entries(gradoData.por_competencia).map(([ceCode, criterios]) => {
        const ceTexto = ceMap[ceCode] ?? "";
        const preview = ceTexto.slice(0, 50) + (ceTexto.length > 50 ? "…" : "");
        return (
          <div key={ceCode} className="border border-border rounded-xl p-4 space-y-2">
            <div className="flex items-start gap-2">
              <Chip size="sm" className="bg-accent/10 text-accent flex-shrink-0 mt-0.5">
                {ceCode}
              </Chip>
              {ceTexto && (
                <p className="text-sm font-medium text-foreground leading-snug">{preview}</p>
              )}
            </div>
            <ol className="list-decimal list-inside space-y-1 pl-1">
              {criterios.map((crit, i) => (
                <li key={i} className="text-sm text-muted-foreground leading-relaxed">
                  {crit}
                </li>
              ))}
            </ol>
          </div>
        );
      })}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ProgramaTab() {
  const [curriculum, setCurriculum] = useState<CurriculumEstructura | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [selectedTramo, setSelectedTramo] = useState<string>("tramo_3");
  const [selectedEspacio, setSelectedEspacio] = useState<string | null>(null);
  const [selectedMateria, setSelectedMateria] = useState<string | null>(null);
  const [selectedGrado, setSelectedGrado] = useState<string>("3er_grado");
  const [activeTab, setActiveTab] = useState<ActiveTab>("ces");

  useEffect(() => {
    getCurriculumEstructura()
      .then((data) => {
        if (Object.keys(data.tramos).length === 0) {
          setError(true);
        } else {
          setCurriculum(data);
        }
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  // Reset downstream selections when tramo changes
  const handleTramoChange = (tramo: string) => {
    setSelectedTramo(tramo);
    setSelectedEspacio(null);
    setSelectedMateria(null);
    setSelectedGrado(TRAMO_GRADES[tramo][0]);
  };

  // Reset materia when espacio changes
  const handleEspacioChange = (espacio: string) => {
    setSelectedEspacio(espacio);
    setSelectedMateria(null);
  };

  const tramos = useMemo<Record<string, Tramo>>(
    () => (curriculum?.tramos ?? {}) as Record<string, Tramo>,
    [curriculum]
  );

  const espacios = useMemo<Record<string, Espacio>>(() => {
    if (!curriculum || !selectedTramo) return {};
    return (tramos[selectedTramo]?.espacios ?? {}) as Record<string, Espacio>;
  }, [curriculum, selectedTramo, tramos]);

  const materias = useMemo<Record<string, Materia>>(() => {
    if (!selectedEspacio) return {};
    return (espacios[selectedEspacio]?.materias ?? {}) as Record<string, Materia>;
  }, [espacios, selectedEspacio]);

  const currentMateria = useMemo<Materia | null>(() => {
    if (!selectedMateria) return null;
    return materias[selectedMateria] ?? null;
  }, [materias, selectedMateria]);

  const gradeKeys = TRAMO_GRADES[selectedTramo] ?? [];

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Spinner color="accent" size="lg" />
        <p className="text-sm text-muted-foreground">Cargando programa curricular…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-5xl w-full mx-auto">
        <Card variant="transparent" className="border border-dashed border-danger/40 p-10 flex flex-col items-center gap-4 text-center">
          <p className="text-sm text-danger">No se pudo cargar el programa curricular.</p>
          <Button
            variant="danger"
            size="sm"
            onPress={() => {
              setError(false);
              setLoading(true);
              getCurriculumEstructura()
                .then((data) => {
                  setCurriculum(data);
                  setLoading(false);
                })
                .catch(() => {
                  setError(true);
                  setLoading(false);
                });
            }}
          >
            Reintentar
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl w-full mx-auto space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div>
        <h2 className="text-xl font-bold text-foreground">Explorador del Programa EBI</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Navegá la estructura curricular: tramos, espacios, materias, contenidos y criterios de logro.
        </p>
      </div>

      {/* ── Tramo selector ──────────────────────────────────────────────────── */}
      <Card variant="default" className="rounded-xl">
        <Card.Content className="p-4 space-y-4">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Tramo
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(tramos).map(([key, tramo]) => (
                <SelectorButton
                  key={key}
                  label={tramo.label}
                  active={selectedTramo === key}
                  onPress={() => handleTramoChange(key)}
                />
              ))}
            </div>
          </div>

          {/* ── Espacio selector ──────────────────────────────────────────── */}
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Espacio curricular
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(espacios).map(([key, espacio]) => (
                <SelectorButton
                  key={key}
                  label={espacio.nombre}
                  active={selectedEspacio === key}
                  onPress={() => handleEspacioChange(key)}
                />
              ))}
            </div>
          </div>

          {/* ── Materia selector ──────────────────────────────────────────── */}
          {selectedEspacio && Object.keys(materias).length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Materia
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(materias).map(([key, materia]) => (
                  <SelectorButton
                    key={key}
                    label={materia.nombre}
                    active={selectedMateria === key}
                    onPress={() => setSelectedMateria(key)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* ── Grado selector ────────────────────────────────────────────── */}
          {selectedMateria && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Grado
              </p>
              <div className="flex flex-wrap gap-2">
                {gradeKeys.map((gKey) => (
                  <SelectorButton
                    key={gKey}
                    label={GRADE_LABELS[gKey] ?? gKey}
                    active={selectedGrado === gKey}
                    onPress={() => setSelectedGrado(gKey)}
                  />
                ))}
              </div>
            </div>
          )}
        </Card.Content>
      </Card>

      {/* ── Content area ────────────────────────────────────────────────────── */}
      {currentMateria ? (
        <Card variant="default" className="rounded-xl">
          <Card.Content className="p-0">
            {/* Tab header */}
            <div className="flex border-b border-border px-4">
              <TabButton
                label="Competencias Específicas"
                active={activeTab === "ces"}
                onPress={() => setActiveTab("ces")}
              />
              <TabButton
                label="Contenidos"
                active={activeTab === "contenidos"}
                onPress={() => setActiveTab("contenidos")}
              />
              <TabButton
                label="Criterios de Logro"
                active={activeTab === "criterios"}
                onPress={() => setActiveTab("criterios")}
              />
            </div>

            {/* Tab body */}
            <div className="p-4">
              {/* Materia title */}
              <div className="mb-4">
                <h3 className="text-base font-bold text-foreground">
                  {currentMateria.nombre}
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {tramos[selectedTramo]?.label} ·{" "}
                  {selectedEspacio ? espacios[selectedEspacio]?.nombre : ""}
                  {activeTab !== "ces" && (
                    <span className="ml-1">
                      · {GRADE_LABELS[selectedGrado] ?? selectedGrado}
                    </span>
                  )}
                </p>
              </div>

              {activeTab === "ces" && (
                <CEAccordion ces={currentMateria.competencias_especificas} />
              )}

              {activeTab === "contenidos" && (
                <ContenidosPanel
                  gradoData={currentMateria.contenidos[selectedGrado]}
                />
              )}

              {activeTab === "criterios" && (
                <CriteriosPanel
                  gradoData={currentMateria.criterios[selectedGrado]}
                  ces={currentMateria.competencias_especificas}
                />
              )}
            </div>
          </Card.Content>
        </Card>
      ) : (
        <Card variant="transparent" className="border border-dashed border-border rounded-xl p-12 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-2xl bg-accent/10 flex items-center justify-center text-accent">
            <BookIcon />
          </div>
          <div>
            <p className="font-semibold text-foreground text-sm">
              {!selectedEspacio
                ? "Seleccioná un espacio curricular para comenzar"
                : !selectedMateria
                ? "Seleccioná una materia para ver sus contenidos"
                : "Seleccioná un grado para ver los contenidos"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Usá los selectores de arriba para navegar el programa.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}

function BookIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}
