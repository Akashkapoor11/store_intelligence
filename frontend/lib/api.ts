/**
 * lib/api.ts — Typed API client for Purplle Store Intelligence API
 */

// In the browser: use relative /api prefix so Next.js rewrites proxy the call to the backend.
// In SSR (Node.js): call the backend directly.
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "/api" : "http://localhost:8000");


async function apiFetch<T>(path: string, defaultVal: T): Promise<T> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      next: { revalidate: 0 },
      cache: "no-store",
    });
    if (!res.ok) return defaultVal;
    return (await res.json()) as T;
  } catch {
    return defaultVal;
  }
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Metrics {
  total_footfall: number;
  total_buyers: number;
  conversion_rate_pct: number;
  avg_dwell_time_sec: number;
  peak_hour: number | null;
  revenue_per_visitor: number;
  total_revenue: number;
  total_orders: number;
  avg_order_value: number;
  staff_count: number;
  timestamp: string;
}

export interface FunnelStage {
  stage: string;
  count: number;
  percentage: number;
  drop_off: number;
}

export interface FunnelData {
  stages: FunnelStage[];
  generated_at: string;
}

export interface ZoneMetrics {
  zone: string;
  unique_visitors: number;
  avg_dwell_seconds: number;
  max_dwell_seconds: number;
  share_of_footfall: number;
}

export interface ZonesData {
  zones: ZoneMetrics[];
  generated_at: string;
}

export interface Anomaly {
  type: string;
  severity: "high" | "medium" | "low";
  description: string;
  timestamp: string | null;
  details: Record<string, unknown> | null;
}

export interface AnomaliesData {
  anomalies: Anomaly[];
  total: number;
  generated_at: string;
}

export interface HourlyBucket {
  hour: number;
  visitors: number;
}

export interface HourlyData {
  hours: HourlyBucket[];
  peak_hour: number | null;
  source: "live" | "demo";
  generated_at: string;
}

export interface DepartmentSales {
  department: string;
  orders: number;
  revenue: number;
  share_pct: number;
}

export interface SalespersonMetrics {
  name: string;
  orders: number;
  revenue: number;
}

export interface BrandMetrics {
  brand: string;
  orders: number;
  revenue: number;
}

export interface SalesData {
  by_department: DepartmentSales[];
  by_salesperson: SalespersonMetrics[];
  top_brands: BrandMetrics[];
  total_orders: number;
  total_revenue: number;
  generated_at: string;
}

export interface HealthData {
  status: string;
  db_connected: boolean;
  event_count: number;
  version: string;
  pipeline_lag_sec?: number;
}

// ── API Calls ─────────────────────────────────────────────────────────────────

export const getMetrics = () =>
  apiFetch<Metrics>("/metrics", {
    total_footfall: 0,
    total_buyers: 0,
    conversion_rate_pct: 0,
    avg_dwell_time_sec: 0,
    peak_hour: null,
    revenue_per_visitor: 0,
    total_revenue: 0,
    total_orders: 0,
    avg_order_value: 0,
    staff_count: 0,
    timestamp: new Date().toISOString(),
  });

export const getFunnel = () =>
  apiFetch<FunnelData>("/funnel", { stages: [], generated_at: "" });

export const getZones = () =>
  apiFetch<ZonesData>("/zones", { zones: [], generated_at: "" });

export const getAnomalies = () =>
  apiFetch<AnomaliesData>("/anomalies", {
    anomalies: [],
    total: 0,
    generated_at: "",
  });

export const getHourly = () =>
  apiFetch<HourlyData>("/hourly", {
    hours: [],
    peak_hour: null,
    source: "demo",
    generated_at: "",
  });

export const getSales = () =>
  apiFetch<SalesData>("/sales", {
    by_department: [],
    by_salesperson: [],
    top_brands: [],
    total_orders: 0,
    total_revenue: 0,
    generated_at: "",
  });

export interface CameraMetrics {
  camera_id:         string;
  primary_zone:      string;
  total_events:      number;
  person_entries:    number;
  zone_entries:      number;
  zone_exits:        number;
  unique_persons:    number;
  avg_dwell_seconds: number;
  staff_detected:    number;
}

export interface CamerasData {
  cameras:      CameraMetrics[];
  generated_at: string;
}

export const getCameras = () =>
  apiFetch<CamerasData>("/cameras", { cameras: [], generated_at: "" });

export interface Insight {
  category:    string;
  priority:    "high" | "medium" | "low";
  title:       string;
  observation: string;
  action:      string;
  metric:      string | null;
}

export interface InsightsData {
  insights:     Insight[];
  total:        number;
  generated_at: string;
  data_source:  string;
}

export const getInsights = () =>
  apiFetch<InsightsData>("/insights", {
    insights: [], total: 0, generated_at: "", data_source: "demo",
  });

export const getHealth = () =>
  apiFetch<HealthData>("/health", {
    status: "offline",
    db_connected: false,
    event_count: 0,
    version: "1.0.0",
  });


