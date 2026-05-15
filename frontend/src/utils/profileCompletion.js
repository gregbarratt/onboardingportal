export const requiredProfileFields = [
  "first_name",
  "last_name",
  "email",
  "personal_email",
  "company_email",
  "phone",
  "business_name",
  "joining_date",
  "address",
  "postcode",
  "commission_bank_name",
  "commission_account_name",
  "commission_sort_code",
  "commission_account_number",
];

export const profileFieldLabels = {
  first_name: "First name",
  last_name: "Last name",
  email: "Email address",
  personal_email: "Personal email",
  company_email: "One Travel Club email",
  phone: "Phone number",
  business_name: "Business name",
  joining_date: "Joining date",
  address: "Address",
  postcode: "Postcode",
  commission_bank_name: "Bank name",
  commission_account_name: "Account name",
  commission_sort_code: "Sort code",
  commission_account_number: "Account number",
};

export function businessNameOrDefault(value) {
  return String(value || "").trim() || "N/A";
}

export function profileWithDefaults(profile = {}, user = null) {
  return {
    first_name: profile.first_name || "",
    last_name: profile.last_name || "",
    email: profile.email || user?.email || "",
    personal_email: profile.personal_email || profile.email || user?.email || "",
    company_email: profile.company_email || "",
    phone: profile.phone || "",
    business_name: businessNameOrDefault(profile.business_name),
    joining_date: profile.joining_date || "",
    address: profile.address || "",
    postcode: profile.postcode || "",
    commission_bank_name: profile.commission_bank_name || "",
    commission_account_name: profile.commission_account_name || "",
    commission_sort_code: profile.commission_sort_code || "",
    commission_account_number: profile.commission_account_number || "",
  };
}

export function normaliseProfileValues(values) {
  return {
    ...values,
    business_name: businessNameOrDefault(values.business_name),
  };
}

export function getMissingProfileFields(profile) {
  if (!profile) return requiredProfileFields;

  return requiredProfileFields.filter((field) => !hasValue(field === "business_name" ? businessNameOrDefault(profile[field]) : profile[field]));
}

export function isProfileComplete(profile) {
  return getMissingProfileFields(profile).length === 0;
}

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}
