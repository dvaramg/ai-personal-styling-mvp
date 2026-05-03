import type { TFunction } from "i18next";

/**
 * Maps backend body-analysis tokens (e.g. `balanced`, `slightly_broad`) to `bodyLabels.*` strings.
 * Falls back to the raw token when no translation exists.
 */
export function translateBodyAnalysisToken(raw: string, t: TFunction): string {
  const key = `bodyLabels.${raw}`;
  const translated = t(key);
  return translated === key ? raw : translated;
}
