import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Analyst",
  description: "Multi-agent market analysis workflow scaffold",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
