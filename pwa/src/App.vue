<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  completeTask,
  createShoppingItem,
  createTask,
  reopenTask,
  dismissEvent,
  snoozeEvent,
  markShoppingBought,
  unmarkShoppingBought,
} from "./api/mutations";
import { usePullRefresh } from "./composables/usePullRefresh";
import { useToast } from "./composables/useToast";
import {
  fetchSnapshot,
  formatDate,
  formatGeneratedAt,
  formatTime,
  type PwaSnapshot,
} from "./api/snapshot";
import { createPairingLink, exchangePairingCode } from "./api/pairing";
import { clearPwaToken, getPwaToken, setPwaToken } from "./auth";
import { sendChatAudio, sendChatMessage } from "./api/chat";
import { uploadPdf } from "./api/documents";
import GeofenceMap from "./components/GeofenceMap.vue";
import { subscribeMyAgentPush } from "./push";

type Tab = "home" | "shopping" | "today" | "chat" | "map";

type ChatLine = { role: "user" | "assistant"; text: string };

const tab = ref<Tab>("home");
const loading = ref(false);
const error = ref("");
const snapshot = ref<PwaSnapshot | null>(null);

const loginToken = ref("");
const authenticated = ref(false);
const busyShopping = ref<Set<number>>(new Set());
const busyTasks = ref<Set<number>>(new Set());
const busyEvents = ref<Set<number>>(new Set());

const addOpen = ref(false);
const addKind = ref<"shopping" | "task">("shopping");
const addName = ref("");
const addExtra = ref("");
const addContext = ref("pessoal");
const addSaving = ref(false);

const pushMsg = ref("");
const pairingOpen = ref(false);
const pairingUrl = ref("");
const pairingBusy = ref(false);

const chatLines = ref<ChatLine[]>([]);
const chatInput = ref("");
const chatBusy = ref(false);
const recording = ref(false);
const pdfContext = ref("pessoal");
const pdfBusy = ref(false);
let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

const { toastMessage, showToast } = useToast();

const contextOptions = [
  { value: "pessoal", label: "Pessoal" },
  { value: "casa", label: "Casa" },
  { value: "theo", label: "Theo" },
  { value: "trabalho", label: "Trabalho" },
];

function openAdd(kind: "shopping" | "task") {
  addKind.value = kind;
  addName.value = "";
  addExtra.value = "";
  addContext.value = "pessoal";
  addOpen.value = true;
}

function openFab() {
  openAdd(tab.value === "today" ? "task" : "shopping");
}

async function submitAdd() {
  const name = addName.value.trim();
  if (!name || addSaving.value) return;
  addSaving.value = true;
  error.value = "";
  try {
    if (addKind.value === "shopping") {
      await createShoppingItem(name, addExtra.value);
      tab.value = "shopping";
    } else {
      await createTask(name, addContext.value);
      tab.value = "today";
    }
    addOpen.value = false;
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(8);
    showToast(addKind.value === "shopping" ? "Item adicionado" : "Tarefa criada");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao salvar";
  } finally {
    addSaving.value = false;
  }
}

const generatedLabel = computed(() =>
  snapshot.value ? formatGeneratedAt(snapshot.value.generated_at) : ""
);

function ensureAuth() {
  authenticated.value = getPwaToken().length > 0;
}

async function load() {
  if (!getPwaToken()) {
    authenticated.value = false;
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    snapshot.value = await fetchSnapshot();
    authenticated.value = true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Erro desconhecido";
    error.value = msg;
    if (msg.includes("Token")) {
      clearPwaToken();
      authenticated.value = false;
    }
  } finally {
    loading.value = false;
  }
}

const { pullY } = usePullRefresh(load, { disabled: loading });

function submitLogin() {
  setPwaToken(loginToken.value);
  loginToken.value = "";
  load();
}

function logout() {
  clearPwaToken();
  snapshot.value = null;
  authenticated.value = false;
}

async function toggleBought(itemId: number) {
  if (busyShopping.value.has(itemId)) return;
  busyShopping.value.add(itemId);
  error.value = "";
  try {
    await markShoppingBought(itemId);
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(12);
    showToast("Marcado como comprado");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao marcar item";
  } finally {
    busyShopping.value.delete(itemId);
  }
}

async function undoBought(itemId: number) {
  if (busyShopping.value.has(itemId)) return;
  busyShopping.value.add(itemId);
  error.value = "";
  try {
    await unmarkShoppingBought(itemId);
    showToast("Compra desfeita");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao desfazer";
  } finally {
    busyShopping.value.delete(itemId);
  }
}

async function markEventDone(eventId: number) {
  if (busyEvents.value.has(eventId)) return;
  busyEvents.value.add(eventId);
  error.value = "";
  try {
    await dismissEvent(eventId);
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(12);
    showToast("Compromisso encerrado");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao encerrar compromisso";
  } finally {
    busyEvents.value.delete(eventId);
  }
}

async function toggleTaskDone(taskId: number) {
  if (busyTasks.value.has(taskId)) return;
  busyTasks.value.add(taskId);
  error.value = "";
  try {
    await completeTask(taskId);
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(12);
    showToast("Tarefa concluída");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao concluir tarefa";
  } finally {
    busyTasks.value.delete(taskId);
  }
}

async function undoTaskDone(taskId: number) {
  if (busyTasks.value.has(taskId)) return;
  busyTasks.value.add(taskId);
  error.value = "";
  try {
    await reopenTask(taskId);
    showToast("Tarefa reaberta");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao reabrir tarefa";
  } finally {
    busyTasks.value.delete(taskId);
  }
}

function doneWhenLabel(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

async function snoozeEventMinutes(eventId: number, minutes: number) {
  if (busyEvents.value.has(eventId)) return;
  busyEvents.value.add(eventId);
  error.value = "";
  try {
    await snoozeEvent(eventId, { minutes });
    showToast(minutes === 15 ? "Adiado 15 min" : `Adiado ${minutes} min`);
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao adiar";
  } finally {
    busyEvents.value.delete(eventId);
  }
}

async function snoozeEventTomorrow(eventId: number) {
  if (busyEvents.value.has(eventId)) return;
  busyEvents.value.add(eventId);
  error.value = "";
  try {
    await snoozeEvent(eventId, { preset: "tomorrow_morning" });
    showToast("Amanhã às 9h");
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao adiar";
  } finally {
    busyEvents.value.delete(eventId);
  }
}

function taskDueLabel(task: PwaSnapshot["tasks_pending"][0]): string {
  if (task.due_at) return formatTime(task.due_at);
  if (task.due_date) return formatDate(task.due_date);
  return "";
}

async function tryPairingFromUrl() {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code")?.trim();
  if (!code) return false;
  error.value = "";
  try {
    const token = await exchangePairingCode(code);
    setPwaToken(token);
    params.delete("code");
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
    window.history.replaceState({}, "", next);
    showToast("Aparelho conectado");
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Pairing falhou";
    return false;
  }
}

async function enablePush() {
  pushMsg.value = "";
  try {
    pushMsg.value = await subscribeMyAgentPush();
    showToast("Notificações ativadas");
  } catch (e) {
    pushMsg.value = e instanceof Error ? e.message : "Erro ao ativar push";
  }
}

async function toggleRecord() {
  if (chatBusy.value) return;
  if (!recording.value) {
    if (!navigator.mediaDevices?.getUserMedia) {
      error.value = "Gravação não suportada neste navegador.";
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };
      mediaRecorder.start();
      recording.value = true;
    } catch {
      error.value = "Permissão de microfone negada.";
    }
    return;
  }
  recording.value = false;
  mediaRecorder?.stop();
  mediaRecorder?.stream.getTracks().forEach((t) => t.stop());
  const blob = new Blob(audioChunks, { type: "audio/webm" });
  if (!blob.size) return;
  chatBusy.value = true;
  chatLines.value.push({ role: "user", text: "🎤 Áudio…" });
  try {
    const res = await sendChatAudio(blob);
    chatLines.value.push({ role: "assistant", text: res.reply });
    await load();
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Falha no áudio";
    error.value = msg;
    chatLines.value.push({ role: "assistant", text: msg });
  } finally {
    chatBusy.value = false;
    mediaRecorder = null;
  }
}

async function onPdfSelected(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || pdfBusy.value) return;
  pdfBusy.value = true;
  error.value = "";
  try {
    const res = await uploadPdf(file, pdfContext.value);
    const extra = res.truncated ? " (truncado no limite de trechos)" : "";
    const msg = `PDF “${res.filename}”: ${res.chunks} trecho(s) na memória${extra}. Pergunte no chat o que quiser sobre o conteúdo.`;
    chatLines.value.push({ role: "assistant", text: msg });
    showToast("PDF indexado");
    if (tab.value !== "chat") tab.value = "chat";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha no PDF";
  } finally {
    pdfBusy.value = false;
  }
}

async function submitChat() {
  const text = chatInput.value.trim();
  if (!text || chatBusy.value) return;
  chatBusy.value = true;
  error.value = "";
  chatLines.value.push({ role: "user", text });
  chatInput.value = "";
  try {
    const res = await sendChatMessage(text);
    chatLines.value.push({ role: "assistant", text: res.reply });
    if (res.llm_outcome === "groq_rate_limit") {
      showToast("Limite Groq — tente em instantes");
    }
    if (res.pending_confirmation) {
      showToast("Confirme no Telegram se pediu confirmação");
    }
    await load();
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Falha no chat";
    error.value = msg;
    chatLines.value.push({ role: "assistant", text: msg });
  } finally {
    chatBusy.value = false;
  }
}

async function openPairingQr() {
  if (pairingBusy.value) return;
  pairingBusy.value = true;
  pairingUrl.value = "";
  try {
    const data = await createPairingLink();
    pairingUrl.value = data.pair_url;
    pairingOpen.value = true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao criar pairing";
  } finally {
    pairingBusy.value = false;
  }
}

onMounted(async () => {
  const paired = await tryPairingFromUrl();
  ensureAuth();
  if (paired || authenticated.value) await load();
});
</script>

<template>
  <div
    class="relative mx-auto flex min-h-dvh max-w-lg flex-col px-4 pb-24 pt-[max(1rem,env(safe-area-inset-top))]"
  >
    <div
      v-if="authenticated && pullY > 0"
      class="pointer-events-none fixed left-0 right-0 top-0 z-50 flex justify-center pt-[max(0.5rem,env(safe-area-inset-top))]"
      :style="{ opacity: Math.min(1, pullY / 72) }"
    >
      <span class="rounded-full bg-slate-800/90 px-3 py-1 text-xs text-slate-200">
        {{ pullY >= 72 ? "Solte para atualizar" : "Puxe para atualizar" }}
      </span>
    </div>
    <div
      v-if="toastMessage"
      class="fixed left-1/2 top-[max(3rem,env(safe-area-inset-top))] z-50 -translate-x-1/2 rounded-xl bg-slate-800 px-4 py-2 text-sm text-white shadow-lg"
      role="status"
    >
      {{ toastMessage }}
    </div>
    <header class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-slate-50">My Agent</h1>
        <p class="text-sm text-slate-400">Mercado, tarefas e chat — igual ao Telegram</p>
      </div>
      <button
        v-if="authenticated"
        type="button"
        class="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300"
        @click="logout"
      >
        Sair
      </button>
    </header>

    <section
      v-if="!authenticated"
      class="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg"
    >
      <h2 class="mb-2 text-lg font-medium">Token de acesso</h2>
      <p class="mb-4 text-sm text-slate-400">
        Cole o <code class="text-slate-300">PWA_API_TOKEN</code>, escaneie um QR de pairing ou abra um link
        <code class="text-slate-300">?code=…</code> gerado no servidor. Só nesta sessão do navegador.
      </p>
      <input
        v-model="loginToken"
        type="password"
        autocomplete="off"
        placeholder="Token"
        class="mb-3 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-sky-500"
        @keyup.enter="submitLogin"
      />
      <button
        type="button"
        class="w-full rounded-xl bg-sky-600 py-3 text-sm font-medium text-white active:bg-sky-700"
        @click="submitLogin"
      >
        Entrar
      </button>
    </section>

    <template v-else>
      <nav class="mb-4 flex gap-1 rounded-xl bg-slate-900 p-1">
        <button
          v-for="t in [
            { id: 'home', label: 'Início' },
            { id: 'chat', label: 'Chat' },
            { id: 'map', label: 'Mapa' },
            { id: 'shopping', label: 'Mercado' },
            { id: 'today', label: 'Hoje' },
          ]"
          :key="t.id"
          type="button"
          class="flex-1 rounded-lg py-2 text-sm font-medium transition"
          :class="tab === t.id ? 'bg-slate-700 text-white' : 'text-slate-400'"
          @click="tab = t.id as Tab"
        >
          {{ t.label }}
        </button>
      </nav>

      <div class="mb-4 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span v-if="generatedLabel">Atualizado: {{ generatedLabel }}</span>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="shrink-0 rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 disabled:opacity-50"
            :disabled="loading"
            @click="load"
          >
            {{ loading ? "..." : "Atualizar" }}
          </button>
          <button
            type="button"
            class="rounded-lg border border-sky-800/60 px-3 py-1.5 text-sky-300"
            @click="enablePush"
          >
            Notificações
          </button>
          <button
            type="button"
            class="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 disabled:opacity-40"
            :disabled="pairingBusy"
            @click="openPairingQr"
          >
            QR aparelho
          </button>
        </div>
      </div>
      <p v-if="pushMsg" class="mb-3 text-xs text-sky-300">{{ pushMsg }}</p>

      <p v-if="error" class="mb-4 rounded-xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
        {{ error }}
      </p>

      <section
        v-if="loading && !snapshot"
        class="animate-pulse space-y-4"
        aria-busy="true"
        aria-label="Carregando"
      >
        <div class="h-24 rounded-2xl bg-slate-800/60" />
        <div class="h-24 rounded-2xl bg-slate-800/60" />
        <div class="h-24 rounded-2xl bg-slate-800/60" />
      </section>

      <section v-else-if="tab === 'home' && snapshot" class="space-y-4">
        <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h3 class="mb-2 font-medium text-slate-200">Mercado</h3>
          <p class="text-3xl font-semibold text-sky-400">{{ snapshot.shopping.count }}</p>
          <p class="text-sm text-slate-400">itens na lista</p>
        </article>
        <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h3 class="mb-2 font-medium text-slate-200">Tarefas pendentes</h3>
          <p class="text-3xl font-semibold text-emerald-400">{{ snapshot.tasks_pending.length }}</p>
        </article>
        <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h3 class="mb-2 font-medium text-slate-200">Compromissos hoje</h3>
          <p class="text-3xl font-semibold text-amber-400">{{ snapshot.events_today.length }}</p>
        </article>
        <p class="text-center text-xs text-slate-500">
          Instale na tela inicial: menu do navegador → “Adicionar à tela inicial”.
        </p>
      </section>

      <section v-else-if="tab === 'chat'" class="flex min-h-0 flex-1 flex-col pb-20">
        <p class="mb-3 text-xs text-slate-500">
          Mesmo assistente do Telegram: mercado, tarefas, agenda, notas e busca na memória.
        </p>
        <div class="mb-3 flex flex-wrap items-center gap-2 text-xs">
          <label class="cursor-pointer rounded-lg border border-slate-600 px-3 py-1.5 text-slate-300">
            {{ pdfBusy ? "PDF…" : "Enviar PDF" }}
            <input
              type="file"
              accept="application/pdf,.pdf"
              class="hidden"
              :disabled="pdfBusy"
              @change="onPdfSelected"
            />
          </label>
          <select
            v-model="pdfContext"
            class="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-300"
          >
            <option v-for="c in contextOptions" :key="c.value" :value="c.value">
              {{ c.label }}
            </option>
          </select>
        </div>
        <ul class="mb-3 max-h-[50vh] flex-1 space-y-2 overflow-y-auto">
          <li
            v-for="(line, i) in chatLines"
            :key="i"
            class="rounded-xl px-3 py-2 text-sm whitespace-pre-wrap"
            :class="
              line.role === 'user'
                ? 'ml-6 bg-sky-950/50 text-sky-100'
                : 'mr-6 border border-slate-800 bg-slate-900/60 text-slate-200'
            "
          >
            {{ line.text }}
          </li>
          <li v-if="!chatLines.length" class="text-center text-sm text-slate-500">
            Pergunte ou registre algo em linguagem natural.
          </li>
        </ul>
        <div class="fixed bottom-[max(5rem,env(safe-area-inset-bottom))] left-0 right-0 z-10 mx-auto max-w-lg px-4">
          <form class="flex gap-2" @submit.prevent="submitChat">
            <input
              v-model="chatInput"
              type="text"
              autocomplete="off"
              placeholder="Mensagem…"
              class="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-sky-500"
              :disabled="chatBusy"
            />
            <button
              type="button"
              class="shrink-0 rounded-xl border px-3 py-3 text-sm"
              :class="
                recording
                  ? 'border-red-600 bg-red-950/50 text-red-200'
                  : 'border-slate-600 text-slate-300'
              "
              :disabled="chatBusy"
              :aria-pressed="recording"
              @click="toggleRecord"
            >
              {{ recording ? "■" : "🎤" }}
            </button>
            <button
              type="submit"
              class="shrink-0 rounded-xl bg-sky-600 px-4 py-3 text-sm font-medium text-white disabled:opacity-50"
              :disabled="chatBusy || !chatInput.trim()"
            >
              {{ chatBusy ? "…" : "Enviar" }}
            </button>
          </form>
        </div>
      </section>

      <section v-else-if="tab === 'map'">
        <GeofenceMap />
      </section>

      <section v-else-if="tab === 'shopping' && snapshot">
        <ul v-if="snapshot.shopping.items.length" class="space-y-2">
          <li
            v-for="item in snapshot.shopping.items"
            :key="item.id"
            class="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3"
          >
            <button
              type="button"
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-sky-700/60 bg-sky-950/40 text-sky-300 disabled:opacity-40"
              :disabled="busyShopping.has(item.id)"
              :aria-label="`Marcar ${item.name} como comprado`"
              @click="toggleBought(item.id)"
            >
              {{ busyShopping.has(item.id) ? "…" : "✓" }}
            </button>
            <span class="flex-1 text-slate-100">
              {{ item.name }}
              <span v-if="item.quantity" class="text-slate-400"> ({{ item.quantity }})</span>
            </span>
          </li>
        </ul>
        <p v-else class="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center text-slate-400">
          Lista vazia.
        </p>
        <div
          v-if="snapshot.shopping.bought_recent?.length"
          class="mt-8 border-t border-slate-800 pt-6"
        >
          <h3 class="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">
            Comprados recentes
          </h3>
          <ul class="space-y-2">
            <li
              v-for="item in snapshot.shopping.bought_recent"
              :key="`b-${item.id}`"
              class="flex items-center gap-3 rounded-xl border border-slate-800/80 bg-slate-950/60 px-4 py-2.5 text-sm opacity-90"
            >
              <span class="flex-1 text-slate-400 line-through">{{ item.name }}</span>
              <button
                type="button"
                class="rounded-lg border border-slate-600 px-2 py-1 text-xs text-slate-300 disabled:opacity-40"
                :disabled="busyShopping.has(item.id)"
                @click="undoBought(item.id)"
              >
                Desfazer
              </button>
            </li>
          </ul>
        </div>
      </section>

      <section v-else-if="tab === 'today' && snapshot" class="space-y-6">
        <div>
          <h3 class="mb-2 text-sm font-medium uppercase tracking-wide text-slate-500">Tarefas</h3>
          <ul v-if="snapshot.tasks_pending.length" class="space-y-2">
            <li
              v-for="task in snapshot.tasks_pending"
              :key="task.id"
              class="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm"
            >
              <button
                type="button"
                class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-emerald-700/60 bg-emerald-950/30 text-emerald-300 disabled:opacity-40"
                :disabled="busyTasks.has(task.id)"
                :aria-label="`Concluir ${task.title}`"
                @click="toggleTaskDone(task.id)"
              >
                {{ busyTasks.has(task.id) ? "…" : "✓" }}
              </button>
              <span class="flex-1">
                <span class="text-slate-400">[{{ task.context }}]</span>
                {{ task.title }}
                <span v-if="taskDueLabel(task)" class="text-slate-500"> · {{ taskDueLabel(task) }}</span>
              </span>
            </li>
          </ul>
          <p v-else class="text-sm text-slate-500">Nenhuma tarefa pendente.</p>
        </div>
        <div v-if="snapshot.tasks_done_recent?.length" class="border-t border-slate-800 pt-6">
          <h3 class="mb-2 text-sm font-medium uppercase tracking-wide text-slate-500">
            Concluídas recentes
          </h3>
          <ul class="space-y-2">
            <li
              v-for="task in snapshot.tasks_done_recent"
              :key="`d-${task.id}`"
              class="flex items-start gap-3 rounded-xl border border-slate-800/80 bg-slate-950/50 px-4 py-2.5 text-sm"
            >
              <span class="flex-1 text-slate-500">
                <span class="text-slate-400">[{{ task.context }}]</span>
                <span class="line-through">{{ task.title }}</span>
                <span v-if="task.completed_at" class="text-slate-600">
                  · {{ doneWhenLabel(task.completed_at) }}
                </span>
              </span>
              <button
                type="button"
                class="shrink-0 rounded-lg border border-slate-600 px-2 py-1 text-xs text-slate-300 disabled:opacity-40"
                :disabled="busyTasks.has(task.id)"
                @click="undoTaskDone(task.id)"
              >
                Reabrir
              </button>
            </li>
          </ul>
        </div>
        <div>
          <h3 class="mb-2 text-sm font-medium uppercase tracking-wide text-slate-500">Compromissos hoje</h3>
          <ul v-if="snapshot.events_today.length" class="space-y-2">
            <li
              v-for="ev in snapshot.events_today"
              :key="ev.id"
              class="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm"
            >
              <button
                type="button"
                class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-amber-700/60 bg-amber-950/30 text-amber-300 disabled:opacity-40"
                :disabled="busyEvents.has(ev.id)"
                :aria-label="`Marcar ${ev.title} como feito`"
                @click="markEventDone(ev.id)"
              >
                {{ busyEvents.has(ev.id) ? "…" : "✓" }}
              </button>
              <span class="flex-1">
                <span class="text-slate-400">[{{ ev.context }}]</span>
                {{ ev.title }}
                <span class="text-slate-500"> · {{ formatTime(ev.start_at) }}</span>
                <span class="mt-2 flex flex-wrap gap-1">
                  <button
                    type="button"
                    class="rounded-md border border-slate-600 px-2 py-0.5 text-[11px] text-slate-300 disabled:opacity-40"
                    :disabled="busyEvents.has(ev.id)"
                    @click="snoozeEventMinutes(ev.id, 15)"
                  >
                    +15 min
                  </button>
                  <button
                    type="button"
                    class="rounded-md border border-slate-600 px-2 py-0.5 text-[11px] text-slate-300 disabled:opacity-40"
                    :disabled="busyEvents.has(ev.id)"
                    @click="snoozeEventTomorrow(ev.id)"
                  >
                    Amanhã 9h
                  </button>
                </span>
              </span>
            </li>
          </ul>
          <p v-else class="text-sm text-slate-500">Nada na agenda hoje.</p>
        </div>
      </section>

      <button
        v-if="tab !== 'chat'"
        type="button"
        class="fixed bottom-[max(1.25rem,env(safe-area-inset-bottom))] right-4 z-20 flex h-14 w-14 items-center justify-center rounded-full bg-sky-600 text-2xl font-light text-white shadow-lg shadow-sky-900/50 active:bg-sky-700"
        aria-label="Adicionar item ou tarefa"
        @click="openFab"
      >
        +
      </button>

      <div
        v-if="pairingOpen"
        class="fixed inset-0 z-30 flex items-center justify-center bg-black/60 p-4"
        @click.self="pairingOpen = false"
      >
        <div class="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-5 text-center shadow-xl">
          <h3 class="mb-2 text-lg font-medium text-slate-100">Conectar outro aparelho</h3>
          <p class="mb-4 text-xs text-slate-400">
            Escaneie com a câmera do celular (código de uso único, ~15 min).
          </p>
          <img
            v-if="pairingUrl"
            class="mx-auto mb-3 rounded-lg bg-white p-2"
            :src="`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(pairingUrl)}`"
            width="220"
            height="220"
            alt="QR pairing"
          />
          <p v-if="pairingUrl" class="mb-4 break-all text-[10px] text-slate-500">{{ pairingUrl }}</p>
          <button
            type="button"
            class="w-full rounded-xl border border-slate-600 py-2.5 text-sm text-slate-300"
            @click="pairingOpen = false"
          >
            Fechar
          </button>
        </div>
      </div>

      <div
        v-if="addOpen"
        class="fixed inset-0 z-30 flex items-end justify-center bg-black/60 p-4"
        @click.self="addOpen = false"
      >
        <div
          class="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-xl"
        >
          <div class="mb-4 flex gap-2">
            <button
              type="button"
              class="flex-1 rounded-lg py-2 text-sm"
              :class="
                addKind === 'shopping'
                  ? 'bg-sky-700 text-white'
                  : 'bg-slate-800 text-slate-400'
              "
              @click="addKind = 'shopping'"
            >
              Mercado
            </button>
            <button
              type="button"
              class="flex-1 rounded-lg py-2 text-sm"
              :class="
                addKind === 'task' ? 'bg-emerald-800 text-white' : 'bg-slate-800 text-slate-400'
              "
              @click="addKind = 'task'"
            >
              Tarefa
            </button>
          </div>
          <input
            v-model="addName"
            type="text"
            :placeholder="addKind === 'shopping' ? 'Nome do item' : 'Título da tarefa'"
            class="mb-3 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-sky-500"
            @keyup.enter="submitAdd"
          />
          <input
            v-if="addKind === 'shopping'"
            v-model="addExtra"
            type="text"
            placeholder="Quantidade (opcional)"
            class="mb-3 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none focus:border-sky-500"
          />
          <select
            v-else
            v-model="addContext"
            class="mb-3 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none"
          >
            <option v-for="c in contextOptions" :key="c.value" :value="c.value">
              {{ c.label }}
            </option>
          </select>
          <div class="flex gap-2">
            <button
              type="button"
              class="flex-1 rounded-xl border border-slate-600 py-3 text-sm text-slate-300"
              @click="addOpen = false"
            >
              Cancelar
            </button>
            <button
              type="button"
              class="flex-1 rounded-xl bg-sky-600 py-3 text-sm font-medium text-white disabled:opacity-50"
              :disabled="addSaving || !addName.trim()"
              @click="submitAdd"
            >
              {{ addSaving ? "Salvando…" : "Salvar" }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>