import Cookies from "js-cookie";
import { jwtDecode } from "jwt-decode";
import type { TokenClaims } from "@/types";

const COOKIE_OPTS = {
  secure: process.env.NODE_ENV === "production",
  sameSite: "strict" as const,
};

export function setTokens(accessToken: string, refreshToken: string) {
  Cookies.set("access_token", accessToken, { ...COOKIE_OPTS, expires: 1 / 96 }); // 15 min
  Cookies.set("refresh_token", refreshToken, { ...COOKIE_OPTS, expires: 7 });
}

export function clearTokens() {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
}

export function getAccessToken(): string | undefined {
  return Cookies.get("access_token");
}

export function getRefreshToken(): string | undefined {
  return Cookies.get("refresh_token");
}

export function getClaims(): TokenClaims | null {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const decoded = jwtDecode<TokenClaims>(token);
    if (decoded.exp * 1000 < Date.now()) return null;
    return decoded;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getClaims() !== null;
}

export function hasPermission(permission: string): boolean {
  const claims = getClaims();
  if (!claims) return false;
  return claims.permissions.includes("*") || claims.permissions.includes(permission);
}

export function hasRole(...roles: string[]): boolean {
  const claims = getClaims();
  if (!claims) return false;
  return roles.includes(claims.role);
}
