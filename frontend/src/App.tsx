import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { SetupPage } from "./pages/SetupPage";

export default function App() {
  return <BrowserRouter><Routes><Route element={<Shell />}><Route path="/" element={<SetupPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Route></Routes></BrowserRouter>;
}
