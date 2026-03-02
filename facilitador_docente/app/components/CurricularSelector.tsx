"use client";

import { useState, useEffect, useMemo } from "react";
import {
  getCiclos,
  getEspaciosByCiclo,
  getUnidadesByEspacio,
  getContenidosByUnidad,
  getGradosByCiclo,
  getContenidosByGradoYUnidad,
  getContenidoDetails,
} from "../actions";

export default function CurricularSelector() {
  const [ciclos, setCiclos] = useState<string[]>([]);
  const [espacios, setEspacios] = useState<string[]>([]);
  const [unidades, setUnidades] = useState<string[]>([]);
  const [grados, setGrados] = useState<string[]>([]);
  const [contenidos, setContenidos] = useState<string[]>([]);

  const [selectedCiclo, setSelectedCiclo] = useState<string>("");
  const [selectedEspacio, setSelectedEspacio] = useState<string>("");
  const [selectedUnidad, setSelectedUnidad] = useState<string>("");
  const [selectedGrado, setSelectedGrado] = useState<string>("");
  const [selectedContenido, setSelectedContenido] = useState<string>("");
  const [contenidoDetails, setContenidoDetails] = useState<any[]>([]);

  const [loading, setLoading] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [openAccordion, setOpenAccordion] = useState<string | null>(null);

  // Initial load
  useEffect(() => {
    setLoading(true);
    getCiclos().then((data) => {
      setCiclos(data);
      setLoading(false);
    });
  }, []);

  // When Ciclo changes
  useEffect(() => {
    setSelectedEspacio("");
    setSelectedGrado("");
    if (selectedCiclo) {
      setLoading(true);
      Promise.all([
        getEspaciosByCiclo(selectedCiclo),
        getGradosByCiclo(selectedCiclo)
      ]).then(([espaciosData, gradosData]) => {
        setEspacios(espaciosData);
        setGrados(gradosData);
        setLoading(false);
      });
    } else {
      setEspacios([]);
      setGrados([]);
    }
  }, [selectedCiclo]);

  // When Espacio changes
  useEffect(() => {
    setSelectedUnidad("");
    if (selectedEspacio) {
      setLoading(true);
      getUnidadesByEspacio(selectedEspacio).then((data) => {
        setUnidades(data);
        setLoading(false);
      });
    } else {
      setUnidades([]);
    }
  }, [selectedEspacio]);

  // When Unidad changes
  useEffect(() => {
    setSelectedContenido("");
    if (selectedUnidad && selectedGrado) {
      setLoading(true);
      getContenidosByGradoYUnidad(selectedGrado, selectedUnidad).then((data) => {
        setContenidos(data);
        setLoading(false);
      });
    } else if (selectedUnidad) {
      setLoading(true);
      getContenidosByUnidad(selectedUnidad).then((data) => {
        setContenidos(data);
        setLoading(false);
      });
    } else {
      setContenidos([]);
    }
  }, [selectedUnidad, selectedGrado]);

  // When Contenido changes
  useEffect(() => {
    if (selectedContenido && selectedUnidad) {
      setDetailsLoading(true);
      getContenidoDetails(selectedContenido, selectedUnidad).then((data) => {
        setContenidoDetails(data);
        setDetailsLoading(false);
        // Auto-open first accordion if available
        if (data.length > 0 && data[0].criterios.length > 0) {
          setOpenAccordion(data[0].criterios[0]);
        }
      });
    } else {
      setContenidoDetails([]);
    }
  }, [selectedContenido, selectedUnidad]);

  // Restructure details grouped by "Criterio de Logro"
  const detailsByCriterio = useMemo(() => {
    const map = new Map();
    contenidoDetails.forEach(detail => {
      detail.criterios.forEach((crit: string) => {
        if (!map.has(crit)) {
          map.set(crit, []);
        }
        map.get(crit).push(detail);
      });
    });
    return Array.from(map.entries());
  }, [contenidoDetails]);

  const selectStyle = {
    padding: "0.85rem",
    borderRadius: "10px",
    border: "1px solid #e2e8f0",
    backgroundColor: "#ffffff",
    fontSize: "0.95rem",
    color: "#1e293b",
    outline: "none",
    transition: "all 0.2s ease-in-out",
    cursor: "pointer",
    width: "100%",
    appearance: "none" as const,
    boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
  };

  const labelStyle = {
    fontWeight: 600,
    fontSize: "0.8rem",
    color: "#64748b",
    marginBottom: "0.5rem",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  };

  const formControlStyle = {
    display: "flex",
    flexDirection: "column" as const,
    marginBottom: "1.5rem",
  };

  return (
    <div
      style={{
        maxWidth: "850px",
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        fontFamily: "'Inter', system-ui, sans-serif",
      }}
    >
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
        gap: "1.25rem",
      }}>
        {/* Ciclo */}
        <div style={formControlStyle}>
          <label htmlFor="ciclo" style={labelStyle}>
            Ciclo Educativo
          </label>
          <select
            id="ciclo"
            value={selectedCiclo}
            onChange={(e) => setSelectedCiclo(e.target.value)}
            style={selectStyle}
          >
            <option value="">Seleccionar Ciclo</option>
            {ciclos.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Grado */}
        <div style={formControlStyle}>
          <label htmlFor="grado" style={labelStyle}>
            Grado / Tramo
          </label>
          <select
            id="grado"
            value={selectedGrado}
            onChange={(e) => setSelectedGrado(e.target.value)}
            disabled={!selectedCiclo || grados.length === 0}
            style={{ ...selectStyle, opacity: (!selectedCiclo || grados.length === 0) ? 0.6 : 1 }}
          >
            <option value="">Seleccionar Grado</option>
            {grados.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </div>

        {/* Espacio */}
        <div style={formControlStyle}>
          <label htmlFor="espacio" style={labelStyle}>
            Espacio
          </label>
          <select
            id="espacio"
            value={selectedEspacio}
            onChange={(e) => setSelectedEspacio(e.target.value)}
            disabled={!selectedCiclo || espacios.length === 0}
            style={{ ...selectStyle, opacity: (!selectedCiclo || espacios.length === 0) ? 0.6 : 1 }}
          >
            <option value="">Seleccionar Espacio</option>
            {espacios.map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
        </div>

        {/* Unidad */}
        <div style={formControlStyle}>
          <label htmlFor="unidad" style={labelStyle}>
            Unidad Curricular
          </label>
          <select
            id="unidad"
            value={selectedUnidad}
            onChange={(e) => setSelectedUnidad(e.target.value)}
            disabled={!selectedEspacio || unidades.length === 0}
            style={{ ...selectStyle, opacity: (!selectedEspacio || unidades.length === 0) ? 0.6 : 1 }}
          >
            <option value="">Seleccionar Unidad</option>
            {unidades.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
        </div>

        {/* Contenido */}
        <div style={{ ...formControlStyle, gridColumn: "1 / -1" }}>
          <label htmlFor="contenido" style={labelStyle}>
            Contenido
          </label>
          <select
            id="contenido"
            value={selectedContenido}
            onChange={(e) => setSelectedContenido(e.target.value)}
            disabled={!selectedGrado || contenidos.length === 0}
            style={{ ...selectStyle, opacity: (!selectedGrado || contenidos.length === 0) ? 0.6 : 1 }}
          >
            <option value="">Seleccionar Contenido</option>
            {contenidos.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: "center", margin: "1rem 0" }}>
          <span style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 500 }}>
             Actualizando opciones...
          </span>
        </div>
      )}

      {/* Detalles del Contenido Restructurado */}
      {selectedContenido && (
        <div style={{
          marginTop: "2.5rem",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}>
         

          {detailsLoading ? (
             <div style={{ textAlign: "center", color: "#64748b", padding: "3rem", backgroundColor: "#ffffff", borderRadius: "12px", border: "1px dashed #e2e8f0" }}>
                Conectando con la red curricular...
             </div>
          ) : contenidoDetails.length > 0 ? (
            <div>
            <div style={{display: "flex", alignItems: "center", gap: "0.5rem"
,marginBottom: "1.5rem",
                  paddingBottom: "1rem",
                  borderBottom: "1px solid #eaeaea"

            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "#3b82f6" }}><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                <h3 style={{
                  fontSize: "1.25rem",
                  color: "#111",
                  
                }}>
              
                  Red de Aprendizaje
                </h3>
            </div>

              {contenidoDetails.map((detail, idx) => (
                <div key={idx} style={{ marginBottom: "2rem", display: "flex", flexDirection: "column", gap: "1.5rem", paddingBottom: "1rem", borderBottom: "1px solid #808080ff" }}>
                        
                        {/* Competencia Especifica */}
                  <div style={{ padding: "1.5rem", backgroundColor: "#f8fafc", borderRadius: "12px", borderLeft: "4px solid #3b82f6" }}>
                    <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "#64748b", margin: "0 0 0.5rem 0" }}>
                      Competencia Específica ({detail.ce_id})
                    </h4>
                    <p style={{ margin: "0 0 1rem 0", color: "#0f172a", fontSize: "1.1rem", fontWeight: 500, lineHeight: 1.5 }}>
                            {detail.ce_enunciado}
                    </p>
                    {detail.ce_desarrollo && (
                      <p style={{ margin: 0, color: "#475569", fontSize: "0.95rem", lineHeight: 1.5 }}>
                            {detail.ce_desarrollo}
                          </p>
                    )}
                        </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "1rem" }}>
                    {/* Criterios de Logro */}
                    <div style={{ padding: "1.5rem", backgroundColor: "#fdf4ff", borderRadius: "12px", border: "1px solid #fbcfe8" }}>
                      <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "#a21caf", margin: "0 0 1rem 0" }}>
                        Criterios de Logro
                      </h4>
                      <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "#701a75" }}>
                        {detail.criterios.map((crit: string, i: number) => (
                          <li key={i} style={{ marginBottom: "0.5rem", fontSize: "0.95rem" }}>{crit}</li>
                        ))}
                        {detail.criterios.length === 0 && <li style={{ listStyle: "none", marginLeft: "-1.2rem", color: "#999" }}>No especificado</li>}
                      </ul>
                              </div>

                    {/* MCNs */}
                    <div style={{ padding: "1.5rem", backgroundColor: "#f0fdfa", borderRadius: "12px", border: "1px solid #ccfbf1" }}>
                      <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "#0d9488", margin: "0 0 1rem 0" }}>
                        Metas de Aprendizaje (MCN)
                      </h4>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                                {detail.mcns.map((mcn: string, i: number) => (
                          <span key={i} style={{
                            backgroundColor: "#ccfbf1",
                            color: "#0f766e",
                            padding: "0.3rem 0.8rem",
                            borderRadius: "999px",
                            fontSize: "0.85rem",
                            fontWeight: 500
                          }}>
                            {mcn}
                          </span>
                                ))}
                        {detail.mcns.length === 0 && <span style={{ color: "#999", fontSize: "0.9rem" }}>No especificado</span>}
                              </div>
                           </div>

                           {/* Ejes */}
                    <div style={{ padding: "1.5rem", backgroundColor: "#fffbeb", borderRadius: "12px", border: "1px solid #fde68a" }}>
                      <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "#b45309", margin: "0 0 1rem 0" }}>
                                Ejes / Competencias
                      </h4>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                                {detail.ejes.map((eje: string, i: number) => (
                          <span key={i} style={{
                            backgroundColor: "#fef3c7",
                            color: "#92400e",
                            padding: "0.3rem 0.8rem",
                            borderRadius: "4px",
                            fontSize: "0.85rem",
                            fontWeight: 500
                          }}>
                            {eje}
                          </span>
                                ))}
                        {detail.ejes.length === 0 && <span style={{ color: "#999", fontSize: "0.9rem" }}>No especificado</span>}
                              </div>
                           </div>
                        </div>

                      </div>
                    ))}
                  </div>
          ) : (
            <p style={{ color: "#888", textAlign: "center" }}>No se encontraron detalles adicionales para este contenido.</p>
          )}
        </div>
      )}
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}} />
    </div>
  );
}
