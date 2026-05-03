export type AppCurrency = "KRW" | "CNY" | "USD";

export const APP_CURRENCIES: AppCurrency[] = ["KRW", "CNY", "USD"];

export const CURRENCY_GLYPH: Record<AppCurrency, string> = {
  KRW: "₩",
  CNY: "¥",
  USD: "$",
};

/** Rough CNY pivot for converting budget amounts when switching currency in the UI. */
export const CURRENCY_TO_CNY: Record<AppCurrency, number> = {
  CNY: 1,
  USD: 7.2,
  KRW: 0.0053,
};

const NUMBER_LOCALE: Record<AppCurrency, string> = {
  KRW: "ko-KR",
  CNY: "zh-CN",
  USD: "en-US",
};

/**
 * Locale-aware money formatting (e.g. ₩30,000 · ¥160 · $22.00).
 * KRW/CNY use whole units; USD keeps two decimals.
 */
export function formatAppPrice(amount: number, currency: AppCurrency): string {
  const fractionDigits = currency === "USD" ? 2 : 0;
  return new Intl.NumberFormat(NUMBER_LOCALE[currency], {
    style: "currency",
    currency,
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: currency === "USD" ? 2 : 0,
  }).format(amount);
}

export function convertAppCurrencyAmount(
  amount: number,
  from: AppCurrency,
  to: AppCurrency,
): number {
  const amountInCny = amount * CURRENCY_TO_CNY[from];
  return amountInCny / CURRENCY_TO_CNY[to];
}

export function defaultCurrencyByLanguage(language: string): AppCurrency {
  if (language.startsWith("ko")) return "KRW";
  if (language.startsWith("zh")) return "CNY";
  return "USD";
}
