import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

type UploadedPhoto = {
  photo_id: string;
  filename: string;
};

type HatRecommendationItem = {
  hat_type: string;
  score?: number;
  image_prompt: string;
  image_url?: string | null;
  image_error_code?: string | null;
};

type HatRecommendResponse = {
  user_id: string;
  recommendations: HatRecommendationItem[];
};

type HatPreviewApiResponse = {
  hat_type?: string | null;
  image_prompt?: string | null;
  image_url?: string | null;
  error_code?: string | null;
  retry_after_sec?: number | null;
  message?: string | null;
};

function Spinner({ label }: { label: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span
        aria-hidden
        style={{
          width: 16,
          height: 16,
          border: "2px solid #c7d2fe",
          borderTopColor: "#4f46e5",
          borderRadius: "50%",
          display: "inline-block",
          animation: "hatPreviewSpin 0.75s linear infinite",
        }}
      />
      <span>{label}</span>
    </span>
  );
}

export function HatRecommendPage() {
  const { t } = useTranslation();
  const [userId, setUserId] = useState("demo-user");
  const [stylePreference, setStylePreference] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploadedPhotos, setUploadedPhotos] = useState<UploadedPhoto[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [result, setResult] = useState<HatRecommendResponse | null>(null);
  const [previewLoadingIndex, setPreviewLoadingIndex] = useState<number | null>(null);
  const [previewErrors, setPreviewErrors] = useState<Record<number, string>>({});
  /** Serialize Replicate usage: one preview request at a time. */
  const previewInFlightRef = useRef(false);
  /** Bumps on each new submit so stale async auto-preview never updates state. */
  const previewSessionRef = useRef(0);

  const runHatPreview = async (
    idx: number,
    item: HatRecommendationItem,
    sessionAtStart: number,
  ) => {
    if (!item.image_prompt.trim()) return;
    if (previewInFlightRef.current) return;
    previewInFlightRef.current = true;
    setErrorText("");
    setPreviewLoadingIndex(idx);
    setPreviewErrors((prev) => {
      const next = { ...prev };
      delete next[idx];
      return next;
    });
    const stale = () => sessionAtStart !== previewSessionRef.current;
    try {
      const res = await fetch("http://localhost:8000/api/v1/hat-recommend/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_prompt: item.image_prompt,
          hat_type: item.hat_type,
        }),
      });
      const data = (await res.json()) as HatPreviewApiResponse;
      if (stale()) return;
      if (!res.ok) {
        const msg = data.message || t("hat.previewGenerateFailed");
        setPreviewErrors((prev) => ({ ...prev, [idx]: msg }));
        return;
      }
      setResult((prev) => {
        if (!prev) return prev;
        const next = prev.recommendations.map((r, i) => {
          if (i !== idx) return r;
          return {
            ...r,
            image_url: data.image_url ?? null,
            image_error_code: data.image_url ? null : data.error_code ?? null,
          };
        });
        return { ...prev, recommendations: next };
      });
      if (data.image_url) {
        setPreviewErrors((prev) => {
          const next = { ...prev };
          delete next[idx];
          return next;
        });
      } else {
        const msg =
          data.error_code === "RATE_LIMIT"
            ? t("recommendation.imageDelayed")
            : data.message || t("hat.generationFailed");
        setPreviewErrors((prev) => ({ ...prev, [idx]: msg }));
      }
    } catch (err) {
      if (stale()) return;
      const msg = t("errors.requestError", { message: String(err) });
      setPreviewErrors((prev) => ({ ...prev, [idx]: msg }));
    } finally {
      previewInFlightRef.current = false;
      if (!stale()) {
        setPreviewLoadingIndex(null);
      }
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files.length) {
      setErrorText(t("hat.needPhoto"));
      setResult(null);
      return;
    }
    previewSessionRef.current += 1;
    const session = previewSessionRef.current;
    setErrorText("");
    setResult(null);
    setPreviewLoadingIndex(null);
    setPreviewErrors({});
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
      const hatData = (await recommendRes.json()) as HatRecommendResponse;
      setResult(hatData);

      const first = hatData.recommendations[0];
      if (first?.image_prompt?.trim()) {
        void (async () => {
          if (session !== previewSessionRef.current) return;
          await runHatPreview(0, first, session);
        })();
      }
    } catch (err) {
      setErrorText(t("errors.requestError", { message: String(err) }));
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const placeholderMessage = (item: HatRecommendationItem) =>
    item.image_error_code === "RATE_LIMIT"
      ? t("recommendation.imageDelayed")
      : t("recommendation.previewPlaceholder");

  const previewBusy = previewLoadingIndex !== null;

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
      <style>{`@keyframes hatPreviewSpin { to { transform: rotate(360deg); } }`}</style>
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
            <option value="korean_basic">{t("style.korean_basic")}</option>
            <option value="minimal">{t("style.minimal")}</option>
            <option value="business">{t("style.business")}</option>
            <option value="casual">{t("style.casual")}</option>
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
          disabled={isLoading || previewBusy}
          style={{
            height: 42,
            border: "none",
            borderRadius: 10,
            background: isLoading || previewBusy ? "#a5b4fc" : "#4f46e5",
            color: "#fff",
            fontWeight: 700,
            cursor: isLoading || previewBusy ? "not-allowed" : "pointer",
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
                gap: 10,
              }}
            >
              <div
                style={{
                  borderRadius: 10,
                  overflow: "hidden",
                  border: "1px solid #dbe2ea",
                  background: "#eef2ff",
                  position: "relative",
                }}
              >
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={t("hat.previewAlt")}
                    style={{
                      width: "100%",
                      height: 200,
                      objectFit: "cover",
                      display: "block",
                    }}
                  />
                ) : (
                  <div
                    style={{
                      height: 200,
                      display: "grid",
                      placeItems: "center",
                      color: "#6366f1",
                      fontSize: 13,
                      fontWeight: 600,
                      padding: "12px 16px",
                      textAlign: "center",
                      background:
                        "linear-gradient(120deg, #eef2ff 0%, #e2e8f0 40%, #eef2ff 100%)",
                    }}
                  >
                    {previewLoadingIndex === idx ? null : placeholderMessage(item)}
                  </div>
                )}
                {previewLoadingIndex === idx ? (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "grid",
                      placeItems: "center",
                      background: "rgba(248, 250, 252, 0.82)",
                      backdropFilter: "blur(2px)",
                    }}
                  >
                    <Spinner label={t("hat.generatingPreview")} />
                  </div>
                ) : null}
              </div>

              <div style={{ display: "grid", gap: 6 }}>
                <strong>
                  {idx + 1}. {t(`hat.types.${item.hat_type}.name`)}
                </strong>
                {item.score != null ? (
                  <span style={{ fontSize: 12, color: "#64748b" }}>
                    {t("hat.scoreLabel")}: {item.score}
                  </span>
                ) : null}
                <span>
                  <strong>{t("hat.reason")}:</strong> {t(`hat.types.${item.hat_type}.reason`)}
                </span>
                <span>
                  <strong>{t("hat.avoid")}:</strong> {t(`hat.types.${item.hat_type}.avoid`)}
                </span>
                <span>
                  <strong>{t("hat.stylingTips")}:</strong> {t(`hat.types.${item.hat_type}.tips`)}
                </span>
              </div>

              <div style={{ display: "grid", gap: 6 }}>
                <button
                  type="button"
                  disabled={previewBusy || !item.image_prompt.trim()}
                  onClick={() => void runHatPreview(idx, item, previewSessionRef.current)}
                  style={{
                    height: 40,
                    borderRadius: 10,
                    border: "1px solid #c7d2fe",
                    background: previewLoadingIndex === idx ? "#e0e7ff" : "#eef2ff",
                    color: "#3730a3",
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: previewBusy || !item.image_prompt.trim() ? "not-allowed" : "pointer",
                    width: "100%",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                  }}
                >
                  {previewLoadingIndex === idx
                    ? t("hat.generatingPreview")
                    : item.image_url
                      ? t("hat.regeneratePreview")
                      : t("hat.generatePreview")}
                </button>
                {previewErrors[idx] ? (
                  <p style={{ margin: 0, color: "#b91c1c", fontSize: 12 }}>{previewErrors[idx]}</p>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
