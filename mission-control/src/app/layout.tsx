import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RadZero // Mission Control HUD",
  description:
    "RadZero In-Situ Fault-Tolerant Inference Runtime for Embedded Edge AI - Real-Time Mission Control HUD & Dynamic Actuator Barrier",
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
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
