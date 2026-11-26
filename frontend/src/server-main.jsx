import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import ServerDashboard from "./ServerDashboard.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ServerDashboard />
  </StrictMode>
);
