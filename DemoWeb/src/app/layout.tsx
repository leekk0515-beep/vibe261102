import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { DatabaseNotice } from "@/components/database-notice";
import { SiteHeader } from "@/components/site-header";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { isDatabaseConfigured } from "@/lib/db";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "데모 게시판",
    template: "%s | 데모 게시판",
  },
  description: "Next.js와 shadcn/ui로 만든 게시판",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <SiteHeader />
          <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 sm:py-8">
            {isDatabaseConfigured() ? children : <DatabaseNotice />}
          </main>
          <footer className="border-t py-6 text-center text-xs text-muted-foreground">
            데모 게시판 · Next.js + shadcn/ui
          </footer>
          <Toaster richColors position="top-center" />
        </ThemeProvider>
      </body>
    </html>
  );
}
