export function formatDate(value) {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not set";

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(value) {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not set";

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatMoney(amount, currency = "GBP") {
  const numericAmount = Number(amount || 0);

  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
  }).format(numericAmount);
}

export function percentage(complete, total) {
  if (!total) return 0;
  return Math.round((complete / total) * 100);
}

export function fullName(profile) {
  if (!profile) return "Agent";
  return [profile.first_name, profile.last_name].filter(Boolean).join(" ") || profile.email || "Agent";
}

export function compactList(items, fallback = "None yet") {
  if (!items?.length) return fallback;
  return items.join(", ");
}
