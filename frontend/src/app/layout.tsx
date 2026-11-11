import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HomeworkDrop",
  description: "Platforma do bezpiecznego przesyłania prac studenckich",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
