import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Field Shift — Adapting Farms with NASA Data",
  description:
    "Decision-support platform for smallholder farmers using NASA Earth observations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="min-h-screen bg-stone-100 antialiased">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
