import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";

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
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased flex flex-col justify-between">
        <AuthProvider>
          <Navbar />
          <div className="flex-1">{children}</div>
        </AuthProvider>
      </body>
    </html>
  );
}
