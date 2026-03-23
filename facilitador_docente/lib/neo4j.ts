import neo4j, { Driver } from "neo4j-driver";

const NEO4J_URI = process.env.NEO4J_URI || "bolt://localhost:7687";
const NEO4J_USER = process.env.NEO4J_USER || "neo4j";
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD || "";

const auth = NEO4J_PASSWORD
  ? neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD)
  : neo4j.auth.none();

// Prevents hot-reloading from creating a huge number of Neo4j driver connections in dev
let driver: Driver;

if (process.env.NODE_ENV === "production") {
  driver = neo4j.driver(NEO4J_URI, auth);
} else {
  // @ts-ignore
  if (!global.neo4jDriver) {
    // @ts-ignore
    global.neo4jDriver = neo4j.driver(NEO4J_URI, auth);
  }
  // @ts-ignore
  driver = global.neo4jDriver;
}

export { driver };
