import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
const base = "/app/";
export default defineConfig({
    base,
    plugins: [
        vue(),
        tailwindcss(),
        VitePWA({
            registerType: "autoUpdate",
            workbox: {
                navigateFallback: `${base}index.html`,
                navigateFallbackDenylist: [/^\/api/],
                runtimeCaching: [
                    {
                        urlPattern: ({ request }) => request.url.includes("/api/pwa/snapshot"),
                        handler: "NetworkFirst",
                        options: {
                            cacheName: "my-agent-snapshot",
                            expiration: { maxEntries: 4, maxAgeSeconds: 60 * 15 },
                            cacheableResponse: { statuses: [0, 200] },
                            networkTimeoutSeconds: 10,
                        },
                    },
                ],
            },
            manifest: {
                name: "My Agent",
                short_name: "My Agent",
                description: "Lista de mercado, tarefas e agenda do dia",
                theme_color: "#1e3a5f",
                background_color: "#0f172a",
                display: "standalone",
                lang: "pt-BR",
                start_url: base,
                scope: base,
                icons: [
                    {
                        src: `${base}icon.svg`,
                        sizes: "any",
                        type: "image/svg+xml",
                        purpose: "any maskable",
                    },
                ],
            },
        }),
    ],
    server: {
        port: 5174,
        proxy: {
            "/api": {
                target: "http://127.0.0.1:8045",
                changeOrigin: true,
            },
        },
    },
    preview: {
        port: 4174,
        proxy: {
            "/api": {
                target: "http://127.0.0.1:8045",
                changeOrigin: true,
            },
        },
    },
});
