import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "leaflet/dist/leaflet.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Field Shift - Adapting Farms with NASA Data",
  description: "Decision-support platform for smallholder farmers using NASA Earth observations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="min-h-screen bg-slate-50 antialiased font-sans">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
