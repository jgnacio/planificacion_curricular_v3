import styles from "./page.module.css";
import CurricularSelector from "./components/CurricularSelector";

export default function Home() {
  return (
    <div
      className={styles.page}
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        backgroundColor: "#f8fafc", // Soft off-white background for the page
        padding: "4rem 1rem",
      }}
    >
      <main
        style={{
          width: "100%",
          maxWidth: "1000px",
          backgroundColor: "#ffffff",
          borderRadius: "20px",
          padding: "3rem",
          boxShadow: "0 20px 60px -15px rgba(0,0,0,0.05)",
          border: "1px solid rgba(0,0,0,0.05)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "3rem" }}>
          <h1
            style={{ 
              color: "#0f172a", 
              margin: 0,
              fontSize: "2.5rem",
              fontWeight: 800,
              letterSpacing: "-0.02em"
            }}
          >
            Facilitador Docente (Beta v0.0.1)
          </h1>
          <p style={{ color: "#64748b", marginTop: "1rem", fontSize: "1.05rem", maxWidth: "700px", margin: "1rem auto 0 auto", lineHeight: "1.6" }}>
            Explorador de competencias, criterios de logro e información basada en la compilación Programas 1er y 2do ciclo.
          </p>
        </div>
        
        <CurricularSelector />
      </main>
    </div>
  );
}
