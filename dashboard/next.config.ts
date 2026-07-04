import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for the docker-compose image (Dockerfile): bundles a
  // minimal server + only the node_modules actually used, instead of
  // shipping the full dev node_modules tree into the runtime image.
  output: "standalone",
};

export default nextConfig;
