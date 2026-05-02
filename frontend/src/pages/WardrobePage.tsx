import { useTranslation } from "react-i18next";

export function WardrobePage() {
  const { t } = useTranslation();
  const sections = t("wardrobe.sections", { returnObjects: true }) as string[];

  return (
    <section
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 14,
        padding: 18,
        background: "#f8fafc",
        display: "grid",
        gap: 12,
      }}
    >
      <h2 style={{ margin: 0, fontSize: 18 }}>{t("wardrobe.title")}</h2>
      <p style={{ margin: 0, color: "#475569", fontSize: 14 }}>
        {t("wardrobe.description")}
      </p>
      {sections.map((item) => (
        <div
          key={item}
          style={{
            border: "1px dashed #cbd5e1",
            borderRadius: 10,
            padding: "12px 14px",
            background: "#fff",
            color: "#334155",
            fontSize: 14,
          }}
        >
          {item}
        </div>
      ))}
    </section>
  );
}
