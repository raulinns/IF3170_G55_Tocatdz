import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

function render() {
  createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
}

if (window.Plotly) {
  render();
} else {
  const script = document.createElement("script");
  script.src = `${import.meta.env.BASE_URL}plotly.min.js`;
  script.onload = render;
  script.onerror = () => {
    document.getElementById("root")!.textContent = "Visualisasi gagal dimuat.";
  };
  document.head.appendChild(script);
}
