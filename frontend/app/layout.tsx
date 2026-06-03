import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Store Intelligence | Brigade Road Analytics",
  description:
    "AI-powered retail store analytics dashboard. Real-time footfall tracking, conversion funnel, zone dwell time, and anomaly detection for Brigade Road store.",
  keywords: "store intelligence, retail analytics, footfall, CCTV, YOLOv8",
  authors: [{ name: "Tech" }],
  openGraph: {
    title: "Store Intelligence",
    description: "Real-time retail analytics powered by AI",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💜</text></svg>" />
      </head>
      <body>{children}</body>
    </html>
  );
}
