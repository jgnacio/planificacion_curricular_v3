CREATE CONSTRAINT FOR (c:CompetenciaEspecifica) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT FOR (m:CompetenciaMCN) REQUIRE m.nombre IS UNIQUE;
CREATE CONSTRAINT FOR (e:EjeTematico) REQUIRE e.nombre IS UNIQUE;
CREATE INDEX FOR (u:Unidad) ON (u.nombre);
CREATE INDEX FOR (t:Tramo) ON (t.nombre);
CREATE INDEX FOR (cont:Contenido) ON (cont.descripcion);
