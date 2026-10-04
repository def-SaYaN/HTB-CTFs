import { NextResponse } from "next/server";

export async function GET() {
  const response = NextResponse.json({
    status: "ok",
    component: "flightdeck-admin",
    parser: "react-flight",
  });
  response.headers.set("X-React-Flight", "enabled");
  response.headers.set("X-RSC-Parser", "server-actions/multipart");
  return response;
}
