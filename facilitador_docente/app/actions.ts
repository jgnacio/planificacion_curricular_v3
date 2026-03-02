"use server";

import { driver } from "@/lib/neo4j";
import type { Record } from "neo4j-driver";

export async function getCiclos() {
  const session = driver.session();
  try {
    const res = await session.run(
      "MATCH (c:Ciclo) RETURN c.nombre as name ORDER BY c.nombre",
    );
    return res.records.map((record: Record) => record.get("name"));
  } catch (error) {
    console.error("Error in getCiclos", error);
    return [];
  } finally {
    await session.close();
  }
}

export async function getEspaciosByCiclo(ciclo: string) {
  const session = driver.session();
  try {
    const res = await session.run(
      "MATCH (e:Espacio)-[:BELONGS_TO]->(c:Ciclo {nombre: $ciclo}) RETURN e.nombre as name ORDER BY e.nombre",
      { ciclo },
    );
    return res.records.map((record: Record) => record.get("name"));
  } catch (error) {
    console.error("Error in getEspaciosByCiclo", error);
    return [];
  } finally {
    await session.close();
  }
}

export async function getUnidadesByEspacio(espacio: string) {
  const session = driver.session();
  try {
    const res = await session.run(
      "MATCH (u:Unidad)-[:BELONGS_TO]->(e:Espacio {nombre: $espacio}) RETURN u.nombre as name ORDER BY u.nombre",
      { espacio },
    );
    return res.records.map((record: Record) => record.get("name"));
  } catch (error) {
    console.error("Error in getUnidadesByEspacio", error);
    return [];
  } finally {
    await session.close();
  }
}

export async function getContenidosByUnidad(unidad: string) {
  const session = driver.session();
  try {
    const prefix = unidad.replace(/ /g, "_").toUpperCase() + "_";
    const res = await session.run(
      `
      MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont:Contenido)
      WHERE ce.id STARTS WITH $prefix
      RETURN DISTINCT cont.descripcion as name
      ORDER BY cont.descripcion
      `,
      { prefix },
    );
    return res.records.map((record: Record) => record.get("name"));
  } catch (error) {
    console.error("Error in getContenidosByUnidad", error);
    return [];
  } finally {
    await session.close();
  }
}

export async function getGradosByCiclo(ciclo: string) {
  const session = driver.session();
  try {
    const res = await session.run(
      `
      MATCH (t:Tramo)-[*1..3]->(c:Ciclo {nombre: $ciclo})
      WITH collect(DISTINCT t.nombre) as tramos
      OPTIONAL MATCH (g:Grado)<-[:SE_ENSEÑA_EN]-(cont:Contenido)<-[:VINCULA_CON]-(ce:CompetenciaEspecifica)-[:BELONGS_TO*1..5]->(c:Ciclo {nombre: $ciclo})
      WITH tramos, collect(DISTINCT g.nombre) as grados
      RETURN tramos, grados
      `,
      { ciclo },
    );
    const tramos = res.records[0]?.get("tramos") || [];
    const grados = res.records[0]?.get("grados") || [];
    return Array.from(new Set([...tramos, ...grados])).sort();
  } catch (error) {
    console.error("Error in getGradosByCiclo", error);
    return [];
  } finally {
    await session.close();
  }
}

export async function getContenidosByGradoYUnidad(grado: string, unidad: string) {
  const session = driver.session();
  try {
    const prefix = unidad.replace(/ /g, "_").toUpperCase() + "_";
    const res = await session.run(
      `
      MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont:Contenido)
      WHERE ce.id STARTS WITH $prefix
      
      OPTIONAL MATCH (ce)-[:BELONGS_TO*1..3]->(t:Tramo {nombre: $grado})
      OPTIONAL MATCH (cont)-[:SE_ENSEÑA_EN]->(g:Grado {nombre: $grado})
      
      WITH cont, t, g
      WHERE t IS NOT NULL OR g IS NOT NULL
      
      RETURN DISTINCT cont.descripcion as name
      ORDER BY cont.descripcion
      `,
      { grado, prefix },
    );
    return res.records.map((record: Record) => record.get("name"));
  } catch (error) {
    console.error("Error in getContenidosByGradoYUnidad", error);
    return [];
  } finally {
    await session.close();
  }
}

export async function getContenidoDetails(contenido: string, unidad: string) {
  const session = driver.session();
  try {
    const prefix = unidad.replace(/ /g, "_").toUpperCase() + "_";
    const res = await session.run(
      `
      MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont:Contenido {descripcion: $contenido})
      WHERE ce.id STARTS WITH $prefix
      
      OPTIONAL MATCH (cont)-[:EVALUADO_POR]->(crit:CriterioLogro)
      OPTIONAL MATCH (ce)-[:CONTRIBUYE_A]->(mcn:CompetenciaMCN)
      OPTIONAL MATCH (ce)-[:PERTENECE_A_EJE]->(eje:Eje)
      
      RETURN 
        ce.id as ce_id,
        ce.enunciado as ce_enunciado,
        ce.desarrollo as ce_desarrollo,
        collect(DISTINCT crit.descripcion) as criterios,
        collect(DISTINCT mcn.nombre) as mcns,
        collect(DISTINCT eje.nombre) as ejes
      `,
      { contenido, prefix }
    );
    
    return res.records.map((record: Record) => ({
      ce_id: record.get("ce_id"),
      ce_enunciado: record.get("ce_enunciado"),
      ce_desarrollo: record.get("ce_desarrollo"),
      criterios: record.get("criterios") || [],
      mcns: record.get("mcns") || [],
      ejes: record.get("ejes") || [],
    }));
  } catch (error) {
    console.error("Error in getContenidoDetails", error);
    return [];
  } finally {
    await session.close();
  }
}
