<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { completeTask, markShoppingBought } from "./api/mutations";
import {
  fetchSnapshot,
  formatDate,
  formatGeneratedAt,
  formatTime,
  type PwaSnapshot,
} from "./api/snapshot";
import { clearPwaToken, getPwaToken, setPwaToken } from "./auth";

type Tab = "home" | "shopping" | "today";

const tab = ref<Tab>("home");
const loading = ref(false);
const error = ref("");
const snapshot = ref<PwaSnapshot | null>(null);

const loginToken = ref("");
const authenticated = ref(false);
const busyShopping = ref<Set<number>>(new Set());
const busyTasks = ref<Set<number>>(new Set());

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
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao marcar item";
  } finally {
    busyShopping.value.delete(itemId);
  }
}

async function toggleTaskDone(taskId: number) {
  if (busyTasks.value.has(taskId)) return;
  busyTasks.value.add(taskId);
  error.value = "";
  try {
    await completeTask(taskId);
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Falha ao concluir tarefa";
  } finally {
    busyTasks.value.delete(taskId);
  }
}

function taskDueLabel(task: PwaSnapshot["tasks_pending"][0]): string {
  if (task.due_at) return formatTime(task.due_at);
  if (task.due_date) return formatDate(task.due_date);
  return "";
}

onMounted(() => {
  ensureAuth();
  if (authenticated.value) load();
});
</script>

<template>
  <div class="mx-auto flex min-h-dvh max-w-lg flex-col px-4 pb-8 pt-[max(1rem,env(safe-area-inset-top))]">
    <header class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-slate-50">My Agent</h1>
        <p class="text-sm text-slate-400">Mercado e tarefas — toque para marcar</p>
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
        Cole o mesmo valor de <code class="text-slate-300">PWA_API_TOKEN</code> do servidor (como no app GF).
        Fica salvo só nesta sessão do navegador.
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

      <div class="mb-4 flex items-center justify-between gap-2 text-xs text-slate-500">
        <span v-if="generatedLabel">Atualizado: {{ generatedLabel }}</span>
        <button
          type="button"
          class="shrink-0 rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 disabled:opacity-50"
          :disabled="loading"
          @click="load"
        >
          {{ loading ? "..." : "Atualizar" }}
        </button>
      </div>

      <p v-if="error" class="mb-4 rounded-xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
        {{ error }}
      </p>

      <section v-if="tab === 'home' && snapshot" class="space-y-4">
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
        <div>
          <h3 class="mb-2 text-sm font-medium uppercase tracking-wide text-slate-500">Compromissos hoje</h3>
          <ul v-if="snapshot.events_today.length" class="space-y-2">
            <li
              v-for="ev in snapshot.events_today"
              :key="ev.id"
              class="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm"
            >
              <span class="text-slate-400">[{{ ev.context }}]</span>
              {{ ev.title }}
              <span class="text-slate-500"> · {{ formatTime(ev.start_at) }}</span>
            </li>
          </ul>
          <p v-else class="text-sm text-slate-500">Nada na agenda hoje.</p>
        </div>
      </section>
    </template>
  </div>
</template>