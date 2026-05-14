import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
// @ts-ignore
import vue from "@vitejs/plugin-vue";
// @ts-ignore
import vueJsx from "@vitejs/plugin-vue-jsx";
import { name, version } from "./package.json";
import { execSync } from "child_process";

let wantsSmallBuild = process.env.GLB_PREVIEW_SMALL_BUILD == "true";

// Helper to safely get git info
function getGitInfo(command: string, fallback: string): string {
  try {
    return execSync(command, { stdio: "pipe" }).toString().trim();
  } catch (e) {
    return fallback;
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  base: "",
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag: string) => tag == "model-viewer",
        },
      },
    }),
    vueJsx(),
  ],
  resolve: {
    alias: {
      // @ts-ignore
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    assetsDir: ".", // Support deploying to a subdirectory using relative URLs
    cssCodeSplit: false, // Small enough to inline
    chunkSizeWarningLimit: 1024, // KB. Three.js is big. Draco is even bigger but not likely to be used.
    sourcemap: true, // For debugging production
    rollupOptions: {
      external: wantsSmallBuild
        ? [
            // Exclude some large optional dependencies if small build is requested (for embedding in python package)
            /three\/examples\/jsm\/libs\/draco\/draco_(en|de)coder\.js/,
          ]
        : [],
    },
  },
  worker: {
    format: "es", // Use ES modules for workers (IIFE is not supported with code-splitting)
  },
  define: {
    __APP_NAME__: JSON.stringify(name),
    __APP_VERSION__: JSON.stringify(version),
    __APP_GIT_SHA__: JSON.stringify(getGitInfo("git rev-parse HEAD", "unknown")),
    __APP_GIT_DIRTY__: JSON.stringify(getGitInfo("git diff --quiet || echo dirty", "")),
    __GLB_PREVIEW_SMALL_BUILD__: JSON.stringify(wantsSmallBuild),
  },
});
