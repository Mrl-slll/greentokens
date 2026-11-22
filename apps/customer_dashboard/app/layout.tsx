import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { AppProvider } from "@/components/AppProvider";
import { Shell } from "@/components/Shell";
export const metadata: Metadata = { title: "GreenTokens" };
export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body><AppProvider><Shell>{children}</Shell></AppProvider></body></html>;
}
