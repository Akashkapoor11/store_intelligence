"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import {
  getMetrics, getFunnel, getZones, getAnomalies,
  getHourly, getSales, getHealth, getInsights,
  Metrics, FunnelData, ZonesData, AnomaliesData,
  HourlyData, SalesData, HealthData, InsightsData,
} from "../lib/api";

// ── Constants ──────────────────────────────────────────────────────────────────
const REFRESH_MS = 5_000;

const FUNNEL_COLORS = ["#a855f7", "#9333ea", "#7c3aed", "#6d28d9"];

// ── Tooltip for recharts ───────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#13132a", border: "1px solid rgba(139,92,246,0.3)",
      borderRadius: 8, padding: "8px 12px", fontSize: "0.78rem", color: "#f1f0ff",
    }}>
      <p style={{ color: "#a09dc0", margin: "0 0 4px" }}>{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ margin: 0, fontWeight: 700, color: "#c084fc" }}>
          {typeof p.value === "number" && p.name === "visitors"
            ? `${p.value} visitors`
            : typeof p.value === "number" && p.name?.includes("dwell")
            ? `${(p.value / 60).toFixed(1)} min`
            : p.value}
        </p>
      ))}
    </div>
  );
};

// ── Skeleton ───────────────────────────────────────────────────────────────────
const Skel = ({ h = 32, w = "100%" }: { h?: number; w?: string }) => (
  <div className="skeleton" style={{ height: h, width: w, borderRadius: 8 }} />
);

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [metrics,   setMetrics]   = useState<Metrics | null>(null);
  const [funnel,    setFunnel]    = useState<FunnelData | null>(null);
  const [zones,     setZones]     = useState<ZonesData | null>(null);
  const [anomalies, setAnomalies] = useState<AnomaliesData | null>(null);
  const [hourly,    setHourly]    = useState<HourlyData | null>(null);
  const [sales,     setSales]     = useState<SalesData | null>(null);
  const [health,    setHealth]    = useState<HealthData | null>(null);
  const [insights,  setInsights]  = useState<InsightsData | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const [m, f, z, a, h, s, hlt, ins] = await Promise.all([
      getMetrics(), getFunnel(), getZones(), getAnomalies(),
      getHourly(), getSales(), getHealth(), getInsights(),
    ]);
    setMetrics(m);
    setFunnel(f);
    setZones(z);
    setAnomalies(a);
    setHourly(h);
    setSales(s);
    setHealth(hlt);
    setInsights(ins);
    setLastRefresh(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, REFRESH_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [refresh]);

  const isOnline = health?.db_connected === true;

  // KPI cards data
  const kpis = [
    {
      icon: "👥", label: "Total Footfall",
      value: loading ? null : (metrics?.total_footfall ?? 0).toLocaleString(),
      sub: "unique customers today",
    },
    {
      icon: "📈", label: "Conversion Rate",
      value: loading ? null : `${(metrics?.conversion_rate_pct ?? 0).toFixed(1)}%`,
      sub: "visitors → buyers",
    },
    {
      icon: "₹", label: "Total Revenue",
      value: loading ? null : `₹${(metrics?.total_revenue ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`,
      sub: "NMV today",
    },
    {
      icon: "🛒", label: "Avg Order Value",
      value: loading ? null : `₹${(metrics?.avg_order_value ?? 0).toFixed(0)}`,
      sub: "per transaction",
    },
    {
      icon: "⏱️", label: "Avg Dwell Time",
      value: loading ? null : `${((metrics?.avg_dwell_time_sec ?? 0) / 60).toFixed(1)}m`,
      sub: "per customer in zone",
    },
  ];

  // Zone bar chart data
  const zoneChartData = (zones?.zones ?? []).map((z) => ({
    zone: z.zone.replace(/_zone$/, "").replace("_", " "),
    visitors: z.unique_visitors,
    dwell: z.avg_dwell_seconds,
    share: z.share_of_footfall,
  }));

  // Hourly chart data
  const hourlyChartData = (hourly?.hours ?? []).map((h) => ({
    time: `${String(h.hour).padStart(2, "0")}:00`,
    visitors: h.visitors,
    isPeak: h.hour === hourly?.peak_hour,
  }));

  return (
    <div className="page-wrapper">

      {/* ── Header ── */}
      <header className="header">
        <div className="header-brand">
          <h1 className="header-title">💜 Store Intelligence</h1>
        </div>
        <div className="header-right">
          {isOnline && health?.pipeline_lag_sec !== undefined && health.pipeline_lag_sec < 90 && (
            <div className="status-badge" style={{ background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.3)" }}>
              <span className="refresh-spinner" style={{ borderColor: "#a855f7", borderRightColor: "transparent" }} />
              <span style={{ color: "#c084fc", fontSize: "0.75rem", fontWeight: 600 }}>Processing CCTV Feed...</span>
            </div>
          )}
          <div className="status-badge">
            <span className={`status-dot${isOnline ? "" : " offline"}`} />
            <span style={{ color: isOnline ? "var(--green)" : "var(--red)" }}>
              {isOnline ? "LIVE" : "OFFLINE"}
            </span>
          </div>
          <div className="refresh-info">
            <span className="refresh-spinner" />
            <span>
              Refreshed {lastRefresh ? lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}
            </span>
          </div>
        </div>
      </header>

      {/* ── KPI Cards ── */}
      <div className="section-label">📊 Key Performance Indicators</div>
      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="kpi-card">
            <span className="kpi-icon">{kpi.icon}</span>
            {kpi.value === null
              ? <Skel h={42} />
              : <div className="kpi-value">{kpi.value}</div>}
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-sub">{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Row: Funnel + Zone Chart ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>

        {/* Conversion Funnel */}
        <div className="chart-card">
          <div className="chart-title">🔽 Conversion Funnel</div>
          <div className="chart-subtitle">Customer journey from entry to purchase</div>
          {loading
            ? <Skel h={200} />
            : (
              <div className="funnel-list">
                {(funnel?.stages ?? []).map((stage, i) => (
                  <div key={stage.stage} className="funnel-stage">
                    <div className="funnel-header">
                      <span className="funnel-stage-name">
                        {stage.stage.replace(/_/g, " ")}
                      </span>
                      <div className="funnel-meta">
                        <span className="funnel-count">{stage.count.toLocaleString()}</span>
                        <span className="funnel-pct">{stage.percentage.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="funnel-track">
                      <div
                        className="funnel-fill"
                        style={{
                          width: `${stage.percentage}%`,
                          background: FUNNEL_COLORS[i] ?? FUNNEL_COLORS[3],
                        }}
                      />
                    </div>
                    {stage.drop_off > 0 && (
                      <div className="funnel-drop">↓ {stage.drop_off.toFixed(1)}% dropped off</div>
                    )}
                  </div>
                ))}
              </div>
            )
          }
        </div>

        {/* Zone Visitors Bar Chart */}
        <div className="chart-card">
          <div className="chart-title">📍 Zone Footfall</div>
          <div className="chart-subtitle">Unique visitors per store zone</div>
          {loading
            ? <Skel h={200} />
            : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={zoneChartData} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                  <XAxis dataKey="zone" tick={{ fill: "#5e5a80", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#5e5a80", fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="visitors" radius={[6, 6, 0, 0]}>
                    {zoneChartData.map((_, i) => (
                      <Cell key={i} fill={`hsl(${270 - i * 20},70%,${65 - i * 5}%)`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )
          }
        </div>
      </div>

      {/* ── Hourly Footfall ── */}
      <div className="section-label">⏱️ Hourly Footfall Pattern</div>
      <div className="chart-card" style={{ marginBottom: 20 }}>
        <div className="chart-title">📊 Visitors by Hour</div>
        <div className="chart-subtitle">
          {hourly?.source === "live" ? "Live data from detection pipeline" : "Demo data (detection pipeline pending)"}
          {hourly?.peak_hour !== null && ` · Peak: ${hourly?.peak_hour}:00`}
        </div>
        {loading
          ? <Skel h={180} />
          : (
            <ResponsiveContainer width="100%" height={190}>
              <AreaChart data={hourlyChartData} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
                <defs>
                  <linearGradient id="footfallGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                <XAxis dataKey="time" tick={{ fill: "#5e5a80", fontSize: 11 }} />
                <YAxis tick={{ fill: "#5e5a80", fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="visitors"
                  stroke="#a855f7"
                  strokeWidth={2}
                  fill="url(#footfallGrad)"
                  dot={(props: any) => {
                    const isPeak = hourlyChartData[props.index]?.isPeak;
                    return isPeak
                      ? <circle key={props.key} cx={props.cx} cy={props.cy} r={5} fill="#ec4899" stroke="#fff" strokeWidth={2} />
                      : <circle key={props.key} cx={props.cx} cy={props.cy} r={3} fill="#a855f7" />;
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )
        }
      </div>

      {/* ── Row: Zone Dwell + Anomalies ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>

        {/* Zone Dwell Time */}
        <div className="chart-card">
          <div className="chart-title">⏳ Avg Dwell Time by Zone</div>
          <div className="chart-subtitle">Minutes customers spend in each area</div>
          {loading
            ? <Skel h={180} />
            : (
              <div className="progress-bar-wrap">
                {(zones?.zones ?? []).map((z) => {
                  const maxDwell = Math.max(...(zones?.zones ?? []).map((x) => x.avg_dwell_seconds), 1);
                  const pct = Math.round((z.avg_dwell_seconds / maxDwell) * 100);
                  return (
                    <div key={z.zone} className="progress-item">
                      <div className="progress-header">
                        <span className="progress-label">{z.zone.replace(/_zone$/, "").replace("_", " ")}</span>
                        <span className="progress-value">{(z.avg_dwell_seconds / 60).toFixed(1)}m</span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
                {(zones?.zones ?? []).length === 0 && (
                  <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", textAlign: "center", padding: "24px 0" }}>
                    Awaiting zone data from detection pipeline…
                  </p>
                )}
              </div>
            )
          }
        </div>

        {/* Anomaly Feed */}
        <div className="chart-card">
          <div className="chart-title">🚨 Anomaly Alerts</div>
          <div className="chart-subtitle">{anomalies?.total ?? 0} active anomalies detected</div>
          {loading
            ? <Skel h={180} />
            : (anomalies?.anomalies ?? []).length > 0
              ? (
                <div className="anomaly-list">
                  {(anomalies?.anomalies ?? []).slice(0, 5).map((a, i) => {
                    const icons = { high: "🔴", medium: "🟡", low: "🔵" };
                    return (
                      <div key={i} className={`anomaly-item ${a.severity}`}>
                        <span className="anomaly-icon">{icons[a.severity]}</span>
                        <div className="anomaly-body">
                          <div className="anomaly-type">{a.type.replace(/_/g, " ")}</div>
                          <div className="anomaly-desc">{a.description}</div>
                        </div>
                        <span className={`anomaly-sev sev-${a.severity}`}>{a.severity}</span>
                      </div>
                    );
                  })}
                </div>
              )
              : (
                <div className="all-clear">
                  <span className="all-clear-icon">✅</span>
                  No anomalies detected — store operating normally
                </div>
              )
          }
        </div>
      </div>

      {/* ── Row: Salesperson Leaderboard + Department Sales ── */}
      <div className="section-label">💰 Sales Intelligence</div>
      <div className="grid-2" style={{ marginBottom: 20 }}>

        {/* Salesperson Leaderboard */}
        <div className="chart-card">
          <div className="chart-title">🏆 Salesperson Leaderboard</div>
          <div className="chart-subtitle">Revenue attributed per staff member</div>
          {loading
            ? <Skel h={180} />
            : (
              <div className="leaderboard">
                {(sales?.by_salesperson ?? []).map((sp, i) => (
                  <div key={sp.name} className="leader-row">
                    <span className={`leader-rank${i === 0 ? " top" : ""}`}>
                      {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${i + 1}`}
                    </span>
                    <div className="leader-avatar">
                      {sp.name.slice(0, 2).toUpperCase()}
                    </div>
                    <span className="leader-name">{sp.name}</span>
                    <span className="leader-orders">{sp.orders} orders</span>
                    <span className="leader-revenue">
                      ₹{sp.revenue.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                ))}
              </div>
            )
          }
        </div>

        {/* Department Sales */}
        <div className="chart-card">
          <div className="chart-title">🏪 Revenue by Department</div>
          <div className="chart-subtitle">Share of total NMV by product category</div>
          {loading
            ? <Skel h={180} />
            : (
              <div className="progress-bar-wrap">
                {(sales?.by_department ?? []).map((dept) => (
                  <div key={dept.department} className="progress-item">
                    <div className="progress-header">
                      <span className="progress-label">{dept.department}</span>
                      <span className="progress-value">
                        ₹{dept.revenue.toLocaleString("en-IN", { maximumFractionDigits: 0 })} ({dept.share_pct}%)
                      </span>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill" style={{ width: `${dept.share_pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )
          }
        </div>
      </div>

      {/* ── Top Brands Bar Chart ── */}
      {!loading && (sales?.top_brands ?? []).length > 0 && (
        <>
          <div className="section-label">🏷️ Top Brands</div>
          <div className="chart-card" style={{ marginBottom: 20 }}>
            <div className="chart-title">💄 Revenue by Brand</div>
            <div className="chart-subtitle">Best-performing brands from today's sales</div>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart
                data={(sales?.top_brands ?? []).map((b) => ({ brand: b.brand, revenue: b.revenue, orders: b.orders }))}
                margin={{ top: 4, right: 8, bottom: 0, left: 10 }}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#5e5a80", fontSize: 11 }} />
                <YAxis type="category" dataKey="brand" tick={{ fill: "#a09dc0", fontSize: 11 }} width={90} />
                <Tooltip
                  formatter={(value: any) => [`₹${Number(value).toLocaleString("en-IN")}`, "Revenue"]}
                  contentStyle={{ background: "#13132a", border: "1px solid rgba(139,92,246,0.3)", borderRadius: 8, color: "#f1f0ff", fontSize: "0.78rem" }}
                />
                <Bar dataKey="revenue" radius={[0, 6, 6, 0]}>
                  {(sales?.top_brands ?? []).map((_, i) => (
                    <Cell key={i} fill={`hsl(${280 - i * 15},65%,${62 - i * 3}%)`} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {/* ── Business Insights Panel ── */}
      {!loading && (insights?.insights ?? []).length > 0 && (
        <>
          <div className="section-label">🧠 Business Insights</div>
          <div className="chart-card" style={{ marginBottom: 20 }}>
            <div className="chart-title">💡 Actionable Store Intelligence</div>
            <div className="chart-subtitle">
              {insights?.total ?? 0} insights derived from footfall + sales data · Source: {insights?.data_source}
            </div>
            <div className="anomaly-list" style={{ marginTop: 16 }}>
              {(insights?.insights ?? []).map((ins, i) => {
                const icons = { high: "🔴", medium: "🟡", low: "🟢" };
                const catIcons: Record<string, string> = {
                  revenue: "💰", staffing: "👥", funnel: "📊", zone: "📍",
                };
                return (
                  <div key={i} className={`anomaly-item ${ins.priority}`}>
                    <span className="anomaly-icon">{catIcons[ins.category] ?? "💡"}</span>
                    <div className="anomaly-body">
                      <div className="anomaly-type">{ins.title}</div>
                      <div className="anomaly-desc" style={{ marginBottom: 4 }}>{ins.observation}</div>
                      <div style={{ fontSize: "0.78rem", color: "var(--purple-400)", fontWeight: 600 }}>
                        ▶ {ins.action}
                      </div>
                      {ins.metric && (
                        <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 2 }}>
                          {ins.metric}
                        </div>
                      )}
                    </div>
                    <span className={`anomaly-sev sev-${ins.priority}`}>{ins.priority}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* ── Footer ── */}
      <footer className="footer">
        <div className="footer-text">
          Store Intelligence System
        </div>
        <div className="footer-text">
          v{health?.version ?? "1.0.0"} ·{" "}
          <a className="footer-link" href="/api/docs" target="_blank" rel="noreferrer">
            API Docs
          </a>
          {" · "}
          <a className="footer-link" href="/api/health" target="_blank" rel="noreferrer">
            Health
          </a>
        </div>
      </footer>
    </div>
  );
}
