import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

// Public URL of the deployed site (set in the GitHub Pages workflow). Link
// previews (LinkedIn, Slack, X) need absolute URLs, so Open Graph tags are
// only emitted when this is known.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
const TITLE = "Team Pulse — zero-input async standups";
const DESCRIPTION =
  "AI-written daily standups from the GitHub, Linear, Notion, and Figma activity your team already produces — plus early warnings when someone looks stuck. Live demo with sample data.";

export const metadata: Metadata = {
  title: "Team Pulse",
  description: DESCRIPTION,
  ...(SITE_URL && {
    openGraph: {
      type: "website",
      url: `${SITE_URL}/`,
      siteName: "Team Pulse",
      title: TITLE,
      description: DESCRIPTION,
      images: [{ url: `${SITE_URL}/og.png`, width: 1150, height: 602, alt: "Team Pulse dashboard" }],
    },
    twitter: {
      card: "summary_large_image",
      title: TITLE,
      description: DESCRIPTION,
      images: [`${SITE_URL}/og.png`],
    },
  }),
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
