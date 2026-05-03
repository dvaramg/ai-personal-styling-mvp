import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { WardrobePage } from "./pages/WardrobePage";
import { HatRecommendPage } from "./pages/HatRecommendPage";
import {
  type AppCurrency,
  APP_CURRENCIES,
  CURRENCY_GLYPH,
  convertAppCurrencyAmount,
  defaultCurrencyByLanguage,
  formatAppPrice,
} from "./utils/currency";
import { translateBodyAnalysisToken } from "./utils/bodyLabels";

type FormState = {
  user_id: string;
  scene: string;
  total_budget: string;
  single_item_budget: string;
  height_cm: string;
  weight_kg: string;
  /** 可选；空则后端用通用日常风格 */
  style_preference: string;
};

type Look = {
  look_id: string;
  image_prompt: string;
  items: {
    top: string;
    bottom: string;
    shoes: string;
    outerwear?: string | null;
    accessories: string[];
  };
  reason_key: string;
  color_key: string;
  fit_key: string;
  scene_note_key: string;
  recommended_size: string;
  estimated_price_krw: number;
  item_fit_reasons: string[];
  scores: {
    body_fit_score: number;
    scene_fit_score: number;
    style_fit_score: number;
    budget_fit_score: number;
    overall_score: number;
  };
  explanation: {
    scores: {
      body_fit_score: number;
      scene_fit_score: number;
      style_fit_score: number;
      budget_fit_score: number;
      overall_score: number;
    };
    why_this_works: string[];
    what_to_avoid: string[];
    improvement_tip: string;
  };
  image_url?: string;
  image_error_code?: string | null;
};

type RecommendResponse = {
  user_id: string;
  looks: Look[];
};

type UploadedPhoto = {
  photo_id: string;
  filename: string;
  content_type?: string | null;
};

type BodyAnalysisProfile = {
  estimated_height_range: string;
  estimated_weight_range: string;
  shoulder_type: string;
  waist_type: string;
  thigh_type: string;
  leg_ratio: string;
  overall_build: string;
  body_subtype: string;
  styling_direction: string;
};

type PageKey = "recommend" | "wardrobe" | "hat";

const SCENE_KEYS = ["daily", "date", "interview", "travel", "school", "work"] as const;

const STYLE_KEYS = ["korean_basic", "minimal", "casual", "street", "vintage", "business"] as const;

const initialState: FormState = {
  user_id: "demo-user",
  scene: "daily",
  total_budget: "",
  single_item_budget: "",
  height_cm: "",
  weight_kg: "",
  style_preference: "",
};

const getPageByPathname = (pathname: string): PageKey => {
  if (pathname === "/hat") return "hat";
  if (pathname === "/wardrobe") return "wardrobe";
  return "recommend";
};

export function App() {
  const { t, i18n } = useTranslation();
  const tItem = (key: string) => t(`items.${key}`, { defaultValue: key });
  const [currentPage, setCurrentPage] = useState<PageKey>(() => getPageByPathname(window.location.pathname));
  const [currency, setCurrency] = useState<AppCurrency>(() => {
    const saved = localStorage.getItem("app_currency") as AppCurrency | null;
    if (saved && APP_CURRENCIES.includes(saved)) {
      return saved;
    }
    return defaultCurrencyByLanguage(navigator.language.toLowerCase());
  });
  const [form, setForm] = useState<FormState>(initialState);
  const [resultText, setResultText] = useState<string>(t("homepage.idleResult"));
  const [resultData, setResultData] = useState<RecommendResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisFiles, setAnalysisFiles] = useState<File[]>([]);
  const [analysisPhotos, setAnalysisPhotos] = useState<UploadedPhoto[]>([]);
  const [analysisProfile, setAnalysisProfile] = useState<BodyAnalysisProfile | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [imageProgressIdx, setImageProgressIdx] = useState(1);

  const parseIntegerInput = (value: string): number | null => {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return null;
    return Math.round(n);
  };

  const bmiCategoryKey = (heightCm: number, weightKg: number): string => {
    const meter = heightCm / 100;
    if (meter <= 0) return "unknown";
    const bmi = weightKg / (meter * meter);
    if (bmi < 18.5) return "under";
    if (bmi < 25) return "normal";
    if (bmi < 30) return "over";
    return "obese";
  };

  const getRecommendationRange = (idx: number) => {
    const totalBudget = parseIntegerInput(form.total_budget) ?? 1000;
    const min = totalBudget * (0.55 + idx * 0.05);
    const max = totalBudget * (0.85 + idx * 0.05);
    return `${formatAppPrice(min, currency)} - ${formatAppPrice(max, currency)}`;
  };

  const onCurrencyChange = (nextCurrency: AppCurrency) => {
    if (nextCurrency === currency) return;
    setForm((prev) => ({
      ...prev,
      total_budget: (() => {
        const parsed = parseIntegerInput(prev.total_budget);
        if (parsed == null) return "";
        return String(Math.round(convertAppCurrencyAmount(parsed, currency, nextCurrency)));
      })(),
      single_item_budget: (() => {
        const parsed = parseIntegerInput(prev.single_item_budget);
        if (parsed == null) return "";
        return String(Math.round(convertAppCurrencyAmount(parsed, currency, nextCurrency)));
      })(),
    }));
    setCurrency(nextCurrency);
    localStorage.setItem("app_currency", nextCurrency);
  };

  const onLanguageChange = async (language: "ko" | "zh" | "en") => {
    await i18n.changeLanguage(language);
    if (!localStorage.getItem("app_currency")) {
      onCurrencyChange(defaultCurrencyByLanguage(language));
    }
  };

  useEffect(() => {
    if (!resultData) {
      setResultText(t("homepage.idleResult"));
    }
  }, [resultData, t]);

  useEffect(() => {
    const onPopState = () => setCurrentPage(getPageByPathname(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!isLoading) {
      setImageProgressIdx(1);
      return;
    }
    setImageProgressIdx(1);
    const timer = window.setInterval(() => {
      setImageProgressIdx((prev) => (prev < 3 ? prev + 1 : 3));
    }, 8000);
    return () => window.clearInterval(timer);
  }, [isLoading]);

  const parseRangeMidpoint = (text: string): number | null => {
    const matches = text.match(/\d+/g);
    if (!matches || matches.length < 2) return null;
    const low = Number(matches[0]);
    const high = Number(matches[1]);
    if (Number.isNaN(low) || Number.isNaN(high)) return null;
    return Math.round((low + high) / 2);
  };

  const navigateToPage = (page: PageKey) => {
    const path = page === "hat" ? "/hat" : page === "wardrobe" ? "/wardrobe" : "/";
    setCurrentPage(page);
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
  };

  const runBodyAnalysis = async (): Promise<BodyAnalysisProfile | null> => {
    if (!analysisFiles.length) {
      return null;
    }
    setIsAnalyzing(true);
    setAnalysisProfile(null);
    try {
      const formData = new FormData();
      formData.append("user_id", form.user_id || "demo-user");
      analysisFiles.slice(0, 2).forEach((file) => formData.append("photos", file));

      const uploadRes = await fetch("http://localhost:8000/api/v1/body-analysis/upload", {
        method: "POST",
        body: formData,
      });
      if (!uploadRes.ok) {
        return null;
      }
      const uploadData = (await uploadRes.json()) as { photos: UploadedPhoto[] };
      setAnalysisPhotos(uploadData.photos);

      const analyzeRes = await fetch("http://localhost:8000/api/v1/body-analysis/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: form.user_id || "demo-user",
          photo_ids: uploadData.photos.map((photo) => photo.photo_id),
        }),
      });
      if (!analyzeRes.ok) {
        return null;
      }
      const analyzeData = (await analyzeRes.json()) as { profile: BodyAnalysisProfile };
      setAnalysisProfile(analyzeData.profile);
      return analyzeData.profile;
    } finally {
      setIsAnalyzing(false);
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!analysisFiles.length) {
      setResultData(null);
      setResultText(t("homepage.needPhoto"));
      return;
    }

    setIsLoading(true);
    try {
      let profile = analysisProfile;
      if (!profile) {
        profile = await runBodyAnalysis();
        if (!profile) {
          setResultData(null);
          setResultText(t("homepage.analysisFailed"));
          return;
        }
      }

      const stylePrefs = form.style_preference.trim()
        ? [form.style_preference.trim()]
        : ["casual"];
      const inferredHeight = parseRangeMidpoint(profile.estimated_height_range) ?? 175;
      const inferredWeight = parseRangeMidpoint(profile.estimated_weight_range) ?? 72;
      const payloadHeight = parseIntegerInput(form.height_cm) ?? inferredHeight;
      const payloadWeight = parseIntegerInput(form.weight_kg) ?? inferredWeight;
      const payloadTotalBudget = parseIntegerInput(form.total_budget) ?? 1000;
      const payloadSingleItemBudget = parseIntegerInput(form.single_item_budget) ?? 400;

      const payload = {
        user_id: form.user_id,
        scene: form.scene,
        total_budget: payloadTotalBudget,
        single_item_budget: payloadSingleItemBudget,
        body_profile: {
          height_cm: payloadHeight,
          weight_kg: payloadWeight,
          body_tags: [] as string[],
        },
        analyzed_body_profile: profile,
        style_preferences: stylePrefs,
      };

      const res = await fetch("http://localhost:8000/api/v1/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorText = await res.text();
        setResultData(null);
        setResultText(`${t("errors.requestFailed", { status: res.status })}\n${errorText}`);
        return;
      }

      const data = await res.json();
      setResultData(data as RecommendResponse);
      setResultText(JSON.stringify(data, null, 2));
    } catch (err) {
      setResultData(null);
      setResultText(t("errors.requestError", { message: String(err) }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)",
        padding: "40px 16px",
        fontFamily:
          'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        color: "#0f172a",
      }}
    >
      <main
        style={{
          maxWidth: 720,
          margin: "0 auto",
          background: "#ffffff",
          border: "1px solid #e2e8f0",
          borderRadius: 18,
          padding: 24,
          boxShadow: "0 12px 30px rgba(15, 23, 42, 0.08)",
        }}
      >
        <header style={{ marginBottom: 24 }}>
          <p
            style={{
              margin: 0,
              color: "#6366f1",
              fontSize: 13,
              letterSpacing: 0.5,
              fontWeight: 700,
              textTransform: "uppercase",
            }}
          >
            {t("common.appTitle")}
          </p>
          <h1 style={{ margin: "8px 0 10px", fontSize: 30, lineHeight: 1.2 }}>
            {t("homepage.heading")}
          </h1>
          <p style={{ margin: 0, color: "#475569", fontSize: 15 }}>
            {t("homepage.subheading")}
          </p>
        </header>

        <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
          <button
            type="button"
            onClick={() => navigateToPage("recommend")}
            style={{
              height: 36,
              borderRadius: 999,
              border: "1px solid #cbd5e1",
              padding: "0 14px",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              background: currentPage === "recommend" ? "#4f46e5" : "#fff",
              color: currentPage === "recommend" ? "#fff" : "#334155",
            }}
          >
            {t("common.pageRecommend")}
          </button>
          <button
            type="button"
            onClick={() => navigateToPage("wardrobe")}
            style={{
              height: 36,
              borderRadius: 999,
              border: "1px solid #cbd5e1",
              padding: "0 14px",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              background: currentPage === "wardrobe" ? "#4f46e5" : "#fff",
              color: currentPage === "wardrobe" ? "#fff" : "#334155",
            }}
          >
            {t("common.pageWardrobe")}
          </button>
          <button
            type="button"
            onClick={() => navigateToPage("hat")}
            style={{
              height: 36,
              borderRadius: 999,
              border: "1px solid #cbd5e1",
              padding: "0 14px",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              background: currentPage === "hat" ? "#4f46e5" : "#fff",
              color: currentPage === "hat" ? "#fff" : "#334155",
            }}
          >
            {t("common.pageHat")}
          </button>
          <select
            value={i18n.language.startsWith("ko") ? "ko" : i18n.language.startsWith("zh") ? "zh" : "en"}
            onChange={(e) => void onLanguageChange(e.target.value as "ko" | "zh" | "en")}
            aria-label={t("common.language")}
            style={{
              height: 36,
              borderRadius: 999,
              border: "1px solid #cbd5e1",
              padding: "0 12px",
              fontSize: 13,
              color: "#334155",
              marginLeft: "auto",
              background: "#fff",
            }}
          >
            <option value="ko">{t("languages.ko")}</option>
            <option value="zh">{t("languages.zh")}</option>
            <option value="en">{t("languages.en")}</option>
          </select>
          <select
            value={currency}
            onChange={(e) => onCurrencyChange(e.target.value as AppCurrency)}
            aria-label={t("common.currency")}
            style={{
              height: 36,
              borderRadius: 999,
              border: "1px solid #cbd5e1",
              padding: "0 12px",
              fontSize: 13,
              color: "#334155",
              background: "#fff",
            }}
          >
            <option value="KRW">{t("currency.KRW")}</option>
            <option value="CNY">{t("currency.CNY")}</option>
            <option value="USD">{t("currency.USD")}</option>
          </select>
        </div>

        {currentPage === "recommend" ? (
          <>
            <section
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 14,
                padding: 18,
                marginBottom: 18,
                background: "#f8fafc",
              }}
            >
              <h2 style={{ margin: "0 0 14px", fontSize: 18 }}>{t("homepage.quickStart")}</h2>
              <form onSubmit={onSubmit} style={{ display: "grid", gap: 14 }}>
            <label style={{ display: "grid", gap: 6, fontSize: 14, fontWeight: 600 }}>
              {t("homepage.photoLabel")}
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => {
                  const files = Array.from(e.target.files ?? []).slice(0, 2);
                  setAnalysisFiles(files);
                  setAnalysisProfile(null);
                  setAnalysisPhotos([]);
                }}
              />
              <span style={{ fontWeight: 400, fontSize: 12, color: "#64748b" }}>
                {t("homepage.photoHint")}
              </span>
            </label>

            {analysisPhotos.length ? (
              <p style={{ margin: 0, fontSize: 13, color: "#334155" }}>
                {t("homepage.selectedUploaded", { names: analysisPhotos.map((p) => p.filename).join("、") })}
              </p>
            ) : analysisFiles.length ? (
              <p style={{ margin: 0, fontSize: 13, color: "#334155" }}>
                {t("homepage.selectedLocal", { names: analysisFiles.map((f) => f.name).join("、") })}
              </p>
            ) : null}

            {analysisProfile ? (
              <div
                style={{
                  border: "1px solid #dbe2ea",
                  borderRadius: 10,
                  padding: 12,
                  background: "#fff",
                  fontSize: 13,
                  color: "#334155",
                }}
              >
                <strong style={{ display: "block", marginBottom: 8 }}>{t("bodyAnalysis.summary")}</strong>
                <div style={{ display: "grid", gap: 8 }}>
                  <span>{t("bodyAnalysis.disclaimer")}</span>
                  <div style={{ borderTop: "1px dashed #e2e8f0", paddingTop: 8, display: "grid", gap: 6 }}>
                    <strong style={{ fontSize: 13 }}>{t("bodyAnalysis.photoEstimatedTraits")}</strong>
                    <span>
                      {t("bodyAnalysis.estimatedHeightRange")}: {analysisProfile.estimated_height_range}
                    </span>
                    <span>
                      {t("bodyAnalysis.estimatedWeightRange")}: {analysisProfile.estimated_weight_range}
                    </span>
                    <span>
                      {t("bodyAnalysis.shoulderType")}:{" "}
                      {translateBodyAnalysisToken(analysisProfile.shoulder_type, t)}
                    </span>
                    <span>
                      {t("bodyAnalysis.waistType")}: {translateBodyAnalysisToken(analysisProfile.waist_type, t)}
                    </span>
                    <span>
                      {t("bodyAnalysis.thighType")}: {translateBodyAnalysisToken(analysisProfile.thigh_type, t)}
                    </span>
                    <span>
                      {t("bodyAnalysis.legRatio")}: {translateBodyAnalysisToken(analysisProfile.leg_ratio, t)}
                    </span>
                    <span>
                      {t("bodyAnalysis.overallBuild")}:{" "}
                      {translateBodyAnalysisToken(analysisProfile.overall_build, t)}
                    </span>
                    <span>
                      {t("bodyAnalysis.bodySubtype")}:{" "}
                      {translateBodyAnalysisToken(analysisProfile.body_subtype, t)}
                    </span>
                  </div>
                  <div style={{ borderTop: "1px dashed #e2e8f0", paddingTop: 8, display: "grid", gap: 6 }}>
                    <strong style={{ fontSize: 13 }}>{t("bodyAnalysis.userCorrectedData")}</strong>
                    {(() => {
                      const manualHeight = parseIntegerInput(form.height_cm);
                      const manualWeight = parseIntegerInput(form.weight_kg);
                      const inferredHeight = parseRangeMidpoint(analysisProfile.estimated_height_range);
                      const inferredWeight = parseRangeMidpoint(analysisProfile.estimated_weight_range);
                      const displayHeight = manualHeight ?? inferredHeight;
                      const displayWeight = manualWeight ?? inferredWeight;
                      const largeDiff =
                        manualWeight != null && inferredWeight != null && Math.abs(manualWeight - inferredWeight) >= 8;
                      return (
                        <>
                          <span>
                            {t("bodyAnalysis.correctedHeight")}{" "}
                            {displayHeight != null ? `${displayHeight}cm` : t("bodyAnalysis.notProvided")}
                          </span>
                          <span>
                            {t("bodyAnalysis.correctedWeight")}{" "}
                            {manualWeight != null ? `${manualWeight}kg` : t("bodyAnalysis.notProvided")}
                          </span>
                          {manualWeight != null ? (
                            <span>
                              {t("bodyAnalysis.photoEstimateWithManual", {
                                estimated: analysisProfile.estimated_weight_range,
                                manual: `${manualWeight}kg`,
                              })}
                            </span>
                          ) : null}
                          {displayHeight != null && displayWeight != null ? (
                            <span>
                              {t("bodyAnalysis.bmiCategory")}: {t(`bodyAnalysis.bmi.${bmiCategoryKey(displayHeight, displayWeight)}`)}
                            </span>
                          ) : null}
                          {largeDiff ? (
                            <span style={{ color: "#7c2d12" }}>{t("bodyAnalysis.manualPriorityNote")}</span>
                          ) : null}
                        </>
                      );
                    })()}
                  </div>
                  {/* TODO: backend should return a stable styling_direction_key so this sentence can be localized. */}
                  <span>
                    {t("bodyAnalysis.stylingDirection")}: {analysisProfile.styling_direction}
                  </span>
                </div>
              </div>
            ) : null}

            <div style={{ display: "grid", gap: 6, gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
              <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 600 }}>
                {t("bodyAnalysis.manualHeightCm")}
                <input
                  type="number"
                  value={form.height_cm}
                  onChange={(e) => setForm({ ...form, height_cm: e.target.value })}
                  placeholder="170"
                  style={{ height: 36, borderRadius: 10, border: "1px solid #cbd5e1", padding: "0 10px" }}
                />
              </label>
              <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 600 }}>
                {t("bodyAnalysis.manualWeightKg")}
                <input
                  type="number"
                  value={form.weight_kg}
                  onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
                  placeholder="70"
                  style={{ height: 36, borderRadius: 10, border: "1px solid #cbd5e1", padding: "0 10px" }}
                />
              </label>
            </div>

            <label style={{ display: "grid", gap: 6, fontSize: 14, fontWeight: 600 }}>
              {t("homepage.sceneLabel")}
              <select
                style={{
                  height: 40,
                  borderRadius: 10,
                  border: "1px solid #cbd5e1",
                  padding: "0 12px",
                  fontSize: 14,
                  background: "#fff",
                }}
                value={form.scene}
                onChange={(e) => setForm({ ...form, scene: e.target.value })}
              >
                {SCENE_KEYS.map((key) => (
                  <option key={key} value={key}>
                    {t(`scene.${key}`)}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: 6, fontSize: 14, fontWeight: 600 }}>
              {t("homepage.totalBudgetLabel")} ({CURRENCY_GLYPH[currency]})
              <input
                style={{
                  height: 40,
                  borderRadius: 10,
                  border: "1px solid #cbd5e1",
                  padding: "0 12px",
                  fontSize: 14,
                }}
                type="number"
                value={form.total_budget}
                onChange={(e) => setForm({ ...form, total_budget: e.target.value })}
                placeholder="1000000"
              />
            </label>

            <label style={{ display: "grid", gap: 6, fontSize: 14, fontWeight: 600 }}>
              {t("homepage.singleBudgetLabel")} ({CURRENCY_GLYPH[currency]})
              <input
                style={{
                  height: 40,
                  borderRadius: 10,
                  border: "1px solid #cbd5e1",
                  padding: "0 12px",
                  fontSize: 14,
                }}
                type="number"
                value={form.single_item_budget}
                onChange={(e) =>
                  setForm({ ...form, single_item_budget: e.target.value })
                }
                placeholder="300000"
              />
            </label>

            <label style={{ display: "grid", gap: 6, fontSize: 14, fontWeight: 600 }}>
              {t("homepage.styleLabel")}
              <select
                style={{
                  height: 40,
                  borderRadius: 10,
                  border: "1px solid #cbd5e1",
                  padding: "0 12px",
                  fontSize: 14,
                  background: "#fff",
                }}
                value={form.style_preference}
                onChange={(e) => setForm({ ...form, style_preference: e.target.value })}
              >
                <option value="">{t("homepage.styleDefault")}</option>
                {STYLE_KEYS.map((key) => (
                  <option key={key} value={key}>
                    {t(`style.${key}`)}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 600, color: "#64748b" }}>
              {t("common.userId")}
              <input
                style={{
                  height: 36,
                  borderRadius: 10,
                  border: "1px solid #e2e8f0",
                  padding: "0 12px",
                  fontSize: 13,
                }}
                value={form.user_id}
                onChange={(e) => setForm({ ...form, user_id: e.target.value })}
              />
            </label>

            <button
              type="submit"
              disabled={isLoading || isAnalyzing}
              style={{
                marginTop: 4,
                height: 44,
                border: "none",
                borderRadius: 10,
                background:
                  isLoading || isAnalyzing
                    ? "linear-gradient(90deg, #a5b4fc 0%, #818cf8 100%)"
                    : "linear-gradient(90deg, #6366f1 0%, #4f46e5 100%)",
                color: "#ffffff",
                fontSize: 15,
                fontWeight: 700,
                cursor: isLoading || isAnalyzing ? "not-allowed" : "pointer",
                boxShadow: "0 10px 20px rgba(79, 70, 229, 0.25)",
              }}
            >
              {isLoading || isAnalyzing ? t("common.processing") : t("homepage.submit")}
            </button>
              </form>
            </section>

            <section
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 14,
                padding: 18,
                background: "#ffffff",
              }}
            >
              <h2 style={{ margin: "0 0 12px", fontSize: 18 }}>{t("recommendation.title")}</h2>
              {isLoading ? (
                <p style={{ margin: "0 0 12px", fontSize: 13, color: "#475569" }}>
                  {t("recommendation.generatingImageProgress", { idx: imageProgressIdx })}
                  {" · "}
                  {t("recommendation.autoGenerating")}
                </p>
              ) : null}
              {resultData?.looks?.length ? (
                <div style={{ display: "grid", gap: 16 }}>
                  {resultData.looks.map((look, idx) => (
                    <article
                      key={look.look_id}
                      style={{
                        border: "1px solid #e2e8f0",
                        borderRadius: 12,
                        padding: 16,
                        background: "#f8fafc",
                        boxShadow: "0 1px 0 rgba(15, 23, 42, 0.04)",
                      }}
                    >
                  <div
                    style={{
                      marginBottom: 12,
                      borderRadius: 10,
                      overflow: "hidden",
                      border: "1px solid #dbe2ea",
                      background: "#eef2ff",
                    }}
                  >
                    {look.image_url ? (
                      <img
                        src={look.image_url}
                        alt={t("recommendation.previewImageAlt", { idx: idx + 1 })}
                        style={{
                          width: "100%",
                          height: 220,
                          objectFit: "cover",
                          display: "block",
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          height: 220,
                          display: "grid",
                          placeItems: "center",
                          color: "#6366f1",
                          fontSize: 13,
                          fontWeight: 600,
                          background:
                            "linear-gradient(120deg, #eef2ff 0%, #e2e8f0 40%, #eef2ff 100%)",
                        }}
                      >
                        <div style={{ display: "grid", gap: 10, justifyItems: "center" }}>
                          <span>
                            {look.image_error_code === "RATE_LIMIT"
                              ? t("recommendation.imageDelayed")
                              : t("recommendation.previewPlaceholder")}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 10,
                    }}
                  >
                    <h3 style={{ margin: 0, fontSize: 16 }}>
                      {t("recommendation.look", { idx: idx + 1 })}
                    </h3>
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#4f46e5",
                        background: "#e0e7ff",
                        borderRadius: 999,
                        padding: "4px 8px",
                      }}
                    >
                      {t("recommendation.option", { idx: idx + 1 })}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
                    <span style={{ fontSize: 12, background: "#eef2ff", color: "#3730a3", padding: "3px 8px", borderRadius: 999 }}>
                      {t("recommendation.bodyFitBadge")} {look.scores.body_fit_score}
                    </span>
                    <span style={{ fontSize: 12, background: "#ecfeff", color: "#0f766e", padding: "3px 8px", borderRadius: 999 }}>
                      {t("recommendation.sceneFitBadge")} {look.scores.scene_fit_score}
                    </span>
                    <span style={{ fontSize: 12, background: "#f0fdf4", color: "#166534", padding: "3px 8px", borderRadius: 999 }}>
                      {t("recommendation.overallBadge")} {look.scores.overall_score}
                    </span>
                  </div>

                  <div style={{ display: "grid", gap: 6, fontSize: 14, color: "#0f172a" }}>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.recommendedSize")}：</strong>
                      {look.recommended_size}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>
                        {t("recommendation.budgetRange", { range: getRecommendationRange(idx) })}
                      </strong>
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.estimatedPrice")}：</strong>
                      {formatAppPrice(
                        convertAppCurrencyAmount(look.estimated_price_krw, "KRW", currency),
                        currency,
                      )}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.top")}：</strong>
                      {tItem(look.items.top)}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.bottom")}：</strong>
                      {tItem(look.items.bottom)}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.shoes")}：</strong>
                      {tItem(look.items.shoes)}
                    </p>
                    {look.items.outerwear ? (
                      <p style={{ margin: 0 }}>
                        <strong>{t("recommendation.outerwear")}：</strong>
                        {tItem(look.items.outerwear)}
                      </p>
                    ) : null}
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.accessories")}：</strong>
                      {look.items.accessories.map((k) => tItem(k)).join(", ") || t("recommendation.none")}
                    </p>
                    {look.item_fit_reasons?.length ? (
                      <p style={{ margin: 0, color: "#475569", fontSize: 12 }}>
                        <strong>{t("recommendation.whyItemFits")}：</strong>
                        {look.item_fit_reasons
                          .map((key) => t(`recommend.itemFitReasons.${key}`, { defaultValue: key }))
                          .join(" / ")}
                      </p>
                    ) : null}
                  </div>

                  <div
                    style={{
                      marginTop: 12,
                      paddingTop: 12,
                      borderTop: "1px dashed #cbd5e1",
                      display: "grid",
                      gap: 8,
                      fontSize: 14,
                      color: "#334155",
                    }}
                  >
                    <p style={{ margin: 0 }}>
                      <strong>{t("homepage.sceneLabel")}：</strong>
                      {t(`recommend.sceneNote.${look.scene_note_key}`)}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.reasonLabel")}：</strong>
                      {t(`recommend.reason.${look.reason_key}`)}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.colorLabel")}：</strong>
                      {t(`recommend.color.${look.color_key}`)}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong>{t("recommendation.fitLabel")}：</strong>
                      {t(`recommend.fit.${look.fit_key}`)}
                    </p>
                  </div>
                    </article>
                  ))}
                </div>
              ) : (
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    background: "#0f172a",
                    color: "#e2e8f0",
                    borderRadius: 10,
                    padding: 14,
                    fontSize: 13,
                    lineHeight: 1.5,
                    overflowX: "auto",
                  }}
                >
                  {resultText}
                </pre>
              )}
            </section>
          </>
        ) : currentPage === "wardrobe" ? (
          <WardrobePage />
        ) : (
          <HatRecommendPage />
        )}
      </main>
    </div>
  );
}
