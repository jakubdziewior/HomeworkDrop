"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

export interface User {
  id: number;
  email: string;
  fullName: string;
  role: "student" | "teacher";
}

interface ApiUser {
  id: number;
  email: string;
  full_name: string;
  role: "student" | "teacher";
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => {
    throw new Error("AuthProvider nie został zainicjalizowany.");
  },
  logout: async () => {},
  refresh: async () => {},
  isLoading: true,
});

function mapUser(apiUser: ApiUser): User {
  return {
    id: apiUser.id,
    email: apiUser.email,
    fullName: apiUser.full_name,
    role: apiUser.role,
  };
}

/**
 * Token JWT przechowywany jest w ciasteczku HttpOnly ustawianym przez backend –
 * JavaScript nie ma do niego dostępu. Stan sesji odtwarzany jest przez /me.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/auth/me", {
        credentials: "same-origin",
        cache: "no-store",
      });
      setUser(res.ok ? mapUser(await res.json()) : null);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    // Usunięcie danych z poprzedniej wersji, która trzymała sesję w localStorage.
    try {
      localStorage.removeItem("homeworkdrop_user");
    } catch {
      // ignore
    }
    refresh().finally(() => setIsLoading(false));
  }, [refresh]);

  const login = async (email: string, password: string): Promise<User> => {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => null);
      const detail = typeof errData?.detail === "string" ? errData.detail : null;
      throw new Error(detail || "Nieprawidłowy adres email lub hasło.");
    }

    const data = await res.json();
    const loggedIn = mapUser(data.user);
    setUser(loggedIn);
    return loggedIn;
  };

  const logout = async () => {
    try {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "same-origin",
      });
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, refresh, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
