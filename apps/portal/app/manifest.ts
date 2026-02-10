import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "USO Partner Portal",
    short_name: "USO Portal",
    description: "Universal Service Orchestrator - Partner and Platform Portal",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#3b82f6",
  };
}
