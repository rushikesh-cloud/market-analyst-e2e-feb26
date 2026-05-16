"use client";

export function readStoredList<T>(key: string, fallback: T[]): T[] {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T[]) : fallback;
  } catch {
    return fallback;
  }
}

export function writeStoredList<T>(key: string, value: T[]) {
  window.localStorage.setItem(key, JSON.stringify(value));
}
