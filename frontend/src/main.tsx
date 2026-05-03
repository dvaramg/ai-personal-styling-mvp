import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./i18n/index";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
