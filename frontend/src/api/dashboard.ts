import { apiClient } from "./client";
import type { DashboardSummary } from "../types";

export function fetchDashboard() {
  return apiClient.get<DashboardSummary>("/dashboard/");
}
