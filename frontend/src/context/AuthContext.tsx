"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export interface User {
  id: number;
  email: string;
  fullName: string;
  role: "student" | "teacher";
}

interface AuthContextType {
  user: User | null;
  login: (user: User) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: () => {},
  logout: () => {},
  isLoading: true,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("homeworkdrop_user");
      if (stored) {
        setUser(JSON.parse(stored));
      }
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = (newUser: User) => {
    setUser(newUser);
    localStorage.setItem("homeworkdrop_user", JSON.stringify(newUser));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("homeworkdrop_user");
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
