"use server";

import { auth } from "@clerk/nextjs/server";

const API_URL = process.env.API_URL ?? "http://localhost:8001";
const ADK_URL = process.env.ADK_URL ?? "http://localhost:8000";
const ADK_APP = "teacher_agent";

// ── Tipos ─────────────────────────────────────────────────────────────────────

export type Planificacion = {
  id: number;
  nombre: string;
  descripcion?: string;
  nivel?: string;
  periodo_inicio?: string;
  periodo_fin?: string;
  chat_exportado?: string;
};

export type Alumno = {
  id: number;
  nombre_completo: string;
  fecha_nacimiento?: string;
  nivel?: string;
  grado?: string;
  notas?: string;
};

// ── Planificaciones ───────────────────────────────────────────────────────────

export async function getPlanificaciones(): Promise<Planificacion[]> {
  try {
    const res = await fetch(`${API_URL}/planificaciones/`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    return [];
  }
}

export async function getPlanificacion(id: number): Promise<Planificacion | null> {
  try {
    const res = await fetch(`${API_URL}/planificaciones/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function createPlanificacion(data: {
  nombre: string;
  descripcion?: string;
  nivel?: string;
  periodo_inicio?: string;
  periodo_fin?: string;
}): Promise<Planificacion | null> {
  try {
    const res = await fetch(`${API_URL}/planificaciones/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function deletePlanificacion(id: number): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/planificaciones/${id}`, { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}

// ── Alumnos ───────────────────────────────────────────────────────────────────

export async function getAlumnos(): Promise<Alumno[]> {
  try {
    const res = await fetch(`${API_URL}/alumnos/`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    return [];
  }
}

export async function createAlumno(data: {
  nombre_completo: string;
  fecha_nacimiento?: string;
  nivel?: string;
  grado?: string;
  notas?: string;
}): Promise<Alumno | null> {
  try {
    const res = await fetch(`${API_URL}/alumnos/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── ADK Chat ──────────────────────────────────────────────────────────────────

export type PdfRef = { filename: string; page: number; label: string };
export type AgentResponse = { text: string; refs: PdfRef[] };

export async function createAdkSession(sessionId: string): Promise<void> {
  const { userId } = await auth();
  const adkUser = userId ?? "anonymous";
  try {
    await fetch(`${ADK_URL}/apps/${ADK_APP}/users/${adkUser}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId }),
    });
  } catch {
    // Session may already exist — ignore
  }
}

export async function sendAdkMessage(
  sessionId: string,
  text: string
): Promise<AgentResponse> {
  const { userId } = await auth();
  const adkUser = userId ?? "anonymous";
  try {
    const res = await fetch(`${ADK_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        appName: ADK_APP,
        userId: adkUser,
        sessionId,
        newMessage: { role: "user", parts: [{ text }] },
        stateDelta: {},
      }),
    });
    if (!res.ok) return { text: "Error al contactar el agente.", refs: [] };
    const data = await res.json();
    return parseAdkResponse(data);
  } catch (e) {
    return { text: `Error de conexión: ${e}`, refs: [] };
  }
}

// ── Curriculum estructurado ───────────────────────────────────────────────────

export type CurriculumEstructura = { tramos: Record<string, any> };

export async function getCurriculumEstructura(): Promise<CurriculumEstructura> {
  try {
    const res = await fetch(`${API_URL}/curriculum/estructura`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    return { tramos: {} };
  }
}

function parseAdkResponse(data: unknown): AgentResponse {
  const buf: string[] = [];

  function process(msg: unknown) {
    if (!msg || typeof msg !== "object") return;
    const m = msg as Record<string, unknown>;
    if (typeof m.text === "string") { buf.push(m.text); return; }
    if (Array.isArray(m.parts)) {
      for (const p of m.parts) {
        if (typeof p === "string") buf.push(p);
        else if (typeof p === "object" && p && typeof (p as Record<string, unknown>).text === "string")
          buf.push((p as Record<string, unknown>).text as string);
      }
      return;
    }
    if (m.content && typeof m.content === "object") {
      const c = m.content as Record<string, unknown>;
      if (Array.isArray(c.parts)) {
        for (const p of c.parts) {
          if (typeof p === "object" && p && typeof (p as Record<string, unknown>).text === "string")
            buf.push((p as Record<string, unknown>).text as string);
        }
        return;
      }
      if (typeof c.text === "string") buf.push(c.text);
    }
  }

  if (Array.isArray(data)) data.forEach(process);
  else process(data);

  const raw = buf.join("").trim() || "El agente no respondió.";

  // Try to parse structured JSON from output_schema
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.text === "string") {
      const refs: PdfRef[] = Array.isArray(parsed.refs)
        ? (parsed.refs as unknown[]).filter(
            (r): r is PdfRef =>
              typeof r === "object" && r !== null &&
              typeof (r as PdfRef).filename === "string" &&
              typeof (r as PdfRef).page === "number"
          )
        : [];
      return { text: parsed.text, refs };
    }
  } catch { /* not JSON — fall through */ }

  return { text: raw, refs: [] };
}
