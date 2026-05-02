import { useState } from "react";
import { useTranslation } from "react-i18next";

type UploadedPhoto = {
  photo_id: string;
  filename: string;
};

type HatRecommendationItem = {
  hat_type: string;
  reason: string;
  avoid: string;
  styling_tips: string;
};

type HatRecommendResponse = {
  user_id: string;
  recommendations: HatRecommendationItem[];
};

export function HatRecommendPage() {
  const { t } = useTranslation();
  const [userId, setUserId] = useState("demo-user");
  const [stylePreference, setStylePreference] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploadedPhotos, setUploadedPhotos] = useState<UploadedPhoto[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [result, setResult] = useState<HatRecommendResponse | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files.length) {
      setErrorText(t("hat.needPhoto"));
      setResult(null);
      return;
    }
    setErrorText("");
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("user_id", userId);
      files.slice(0, 2).forEach((file) => formData.append("photos", file));

      const uploadRes = await fetch("http://localhost:8000/api/v1/hat-recommend/upload", {
        method: "POST",
        body: formData,
      });
      if (!uploadRes.ok) {
        setErrorText(t("hat.uploadFailed"));
        setResult(null);
        return;
      }
      const uploadData = (await uploadRes.json()) as { photos: UploadedPhoto[] };
      setUploadedPhotos(uploadData.photos);

      const recommendRes = await fetch("http://localhost:8000/api/v1/hat-recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          photo_ids: uploadData.photos.map((p) => p.photo_id),
          style_preference: stylePreference,
        }),
      });
      if (!recommendRes.ok) {
        setErrorText(t("hat.recommendFailed"));
        setResult(null);
        return;
      }
      setResult((await recommendRes.json()) as HatRecommendResponse);
    } catch (err) {
      setErrorText(`请求异常: ${String(err)}`);
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 14,
        padding: 18,
        background: "#f8fafc",
        display: "grid",
        gap: 14,
      }}
    >
      <h2 style={{ margin: 0, fontSize: 20 }}>{t("hat.title")}</h2>
      <p style={{ margin: 0, color: "#475569", fontSize: 14 }}>
        {t("hat.description")}
      </p>

      <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
        <label style={{ display: "grid", gap: 6, fontSize: 14, fontWeight: 600 }}>
          {t("hat.photoLabel")}
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files ?? []).slice(0, 2))}
          />
        </label>

        <label style={{ display: "grid", gap: 6, fontSize: 14, fontWeight: 600 }}>
          {t("hat.styleLabel")}
          <select
            value={stylePreference}
            onChange={(e) => setStylePreference(e.target.value)}
            style={{ height: 40, borderRadius: 10, border: "1px solid #cbd5e1", padding: "0 12px" }}
          >
            <option value="">{t("hat.defaultStyle")}</option>
            <option value={t("stylePreference.korean")}>{t("stylePreference.korean")}</option>
            <option value={t("stylePreference.minimal")}>{t("stylePreference.minimal")}</option>
            <option value={t("stylePreference.business")}>{t("stylePreference.business")}</option>
          </select>
        </label>

        <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 600, color: "#64748b" }}>
          {t("hat.userId")}
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ height: 36, borderRadius: 10, border: "1px solid #e2e8f0", padding: "0 12px" }}
          />
        </label>

        <button
          type="submit"
          disabled={isLoading}
          style={{
            height: 42,
            border: "none",
            borderRadius: 10,
            background: isLoading ? "#a5b4fc" : "#4f46e5",
            color: "#fff",
            fontWeight: 700,
            cursor: isLoading ? "not-allowed" : "pointer",
          }}
        >
          {isLoading ? t("common.processing") : t("hat.submit")}
        </button>
      </form>

      {uploadedPhotos.length ? (
        <p style={{ margin: 0, fontSize: 13, color: "#334155" }}>
          {t("hat.uploaded", { names: uploadedPhotos.map((p) => p.filename).join("、") })}
        </p>
      ) : null}

      {errorText ? (
        <p style={{ margin: 0, color: "#b91c1c", fontSize: 13 }}>{errorText}</p>
      ) : null}

      {result?.recommendations?.length ? (
        <div style={{ display: "grid", gap: 10 }}>
          {result.recommendations.slice(0, 3).map((item, idx) => (
            <article
              key={`${item.hat_type}-${idx}`}
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 10,
                padding: 12,
                background: "#fff",
                display: "grid",
                gap: 6,
              }}
            >
              <strong>{idx + 1}. {item.hat_type}</strong>
              <span><strong>{t("hat.reason")}:</strong> {item.reason}</span>
              <span><strong>{t("hat.avoid")}:</strong> {item.avoid}</span>
              <span><strong>{t("hat.stylingTips")}:</strong> {item.styling_tips}</span>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
