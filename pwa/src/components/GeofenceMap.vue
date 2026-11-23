<script setup lang="ts">
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { onMounted, onUnmounted, ref, watch } from "vue";
import { fetchGeofenceEvents, type GeofenceEventRow } from "../api/geofence";

const MOGI: [number, number] = [-23.5225, -46.1858];

const mapEl = ref<HTMLElement | null>(null);
const events = ref<GeofenceEventRow[]>([]);
const loading = ref(false);
const error = ref("");

let map: L.Map | null = null;
let layer: L.LayerGroup | null = null;

function statusLabel(s: string): string {
  if (s === "sent") return "Lista enviada";
  if (s === "empty") return "Lista vazia";
  return s;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    events.value = await fetchGeofenceEvents();
    renderMarkers();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Erro";
  } finally {
    loading.value = false;
  }
}

function renderMarkers() {
  if (!map || !layer) return;
  layer.clearLayers();
  const withCoords = events.value.filter(
    (e) => e.latitude != null && e.longitude != null
  );
  for (const ev of withCoords) {
    const lat = ev.latitude as number;
    const lon = ev.longitude as number;
    const title = ev.location_label || "Geofence";
    const body = `${statusLabel(ev.status)} · ${ev.items_count} itens · ${new Date(ev.created_at).toLocaleString("pt-BR")}`;
    L.circleMarker([lat, lon], { radius: 8, color: "#38bdf8", fillOpacity: 0.85 })
      .bindPopup(`<strong>${title}</strong><br/>${body}`)
      .addTo(layer);
  }
  if (withCoords.length) {
    const bounds = L.latLngBounds(withCoords.map((e) => [e.latitude!, e.longitude!]));
    map.fitBounds(bounds, { padding: [24, 24], maxZoom: 15 });
  } else {
    map.setView(MOGI, 12);
  }
}

onMounted(() => {
  if (!mapEl.value) return;
  map = L.map(mapEl.value).setView(MOGI, 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
    maxZoom: 19,
  }).addTo(map);
  layer = L.layerGroup().addTo(map);
  load();
});

onUnmounted(() => {
  map?.remove();
  map = null;
});

watch(events, () => renderMarkers());
</script>

<template>
  <div class="space-y-3">
    <p class="text-xs text-slate-500">
      Disparos do MacroDroid (webhook geofence). Envie
      <code class="text-slate-400">lat</code> e <code class="text-slate-400">lon</code> no JSON para
      marcar no mapa. Instruções: <a class="text-sky-400" href="/macro/" target="_blank">/macro/</a>
    </p>
    <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    <div
      ref="mapEl"
      class="h-56 w-full rounded-xl border border-slate-800 bg-slate-900"
      role="img"
      aria-label="Mapa de alertas geofence"
    />
    <button
      type="button"
      class="text-xs text-sky-400"
      :disabled="loading"
      @click="load"
    >
      {{ loading ? "Atualizando…" : "Atualizar mapa" }}
    </button>
    <ul v-if="events.length" class="max-h-40 space-y-1 overflow-y-auto text-xs text-slate-400">
      <li v-for="ev in events.slice(0, 15)" :key="ev.id">
        <span class="text-slate-300">{{ ev.location_label || "—" }}</span>
        · {{ statusLabel(ev.status) }} ({{ ev.items_count }})
        · {{ new Date(ev.created_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) }}
      </li>
    </ul>
    <p v-else-if="!loading" class="text-xs text-slate-500">Nenhum alerta registrado ainda.</p>
  </div>
</template>