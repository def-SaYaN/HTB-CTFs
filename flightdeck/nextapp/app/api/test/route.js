import { NextResponse } from "next/server";

// Difficulty dial: this endpoint confirms the stack + version for players who
// find it. Remove this file (and rebuild) to make Stage 3 harder - players
// would then have to read package.json on disk after foothold.
export async function GET() {
  let nextVer = "unknown";
  let reactVer = "unknown";
  try {
    nextVer = require("next/package.json").version;
  } catch (_) {}
  try {
    reactVer = require("react/package.json").version;
  } catch (_) {}
  return NextResponse.json({
    status: "ok",
    service: "flightdeck-admin",
    versions: { nextjs: nextVer, react: reactVer },
    rsc_enabled: true,
    server_actions: true,
    flight_protocol: "enabled",
    advisory: "RSC deserialization advisory pending review",
  });
}
