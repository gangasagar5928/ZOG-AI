import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mission Control HUD | Member 2 (Prachi)",
  description:
    "Antigravity Real-Time Spacecraft Mission Control HUD, Telemetry Engine & Dynamic Actuator Invariant Barrier",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0D1117] text-[#C9D1D9] antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
