import { initializeApp, getApps, getApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";

// Your web app's Firebase configuration
export const firebaseConfig = {
  apiKey: "AIzaSyAOMI8s9jvjCmizNwUWM4McacGcrh6VIc0",
  authDomain: "radzero.firebaseapp.com",
  projectId: "radzero",
  storageBucket: "radzero.firebasestorage.app",
  messagingSenderId: "820433840076",
  appId: "1:820433840076:web:b769800c02159011afdf69",
  measurementId: "G-9MGDLPE2QN",
};

// Initialize Firebase (SSR-safe singleton)
export const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();

export const initAnalytics = async () => {
  if (typeof window !== "undefined" && (await isSupported())) {
    return getAnalytics(app);
  }
  return null;
};
