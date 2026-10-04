"use server";

// A trivial Server Action. Its mere existence exposes the React Server
// Components "Flight" endpoint that CVE-2025-55182 (React2Shell) abuses via
// unsafe deserialization of the request payload. No special logic is needed
// here; the vulnerability lives in the vulnerable react-server-dom-webpack
// deserializer pinned in package.json, not in this function.
export async function recordDeployNote(formData) {
  const note = formData.get("note") || "";
  return { ok: true, length: String(note).length };
}
