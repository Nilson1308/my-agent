<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  completeTask,
  createShoppingItem,
  createTask,
  reopenTask,
  dismissEvent,
  markShoppingBought,
  unmarkShoppingBought,
} from "./api/mutations";
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
const busyEvents = ref<Set<number>>(new Set());

const addOpen = ref(false);
const addKind = ref<"shopping" | "task">("shopping");
const addName = ref("");
const addExtra = ref("");
const addContext = ref("pessoal");
const addSaving = ref(false);

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
  <div
    class="relative mx-auto flex min-h-dvh max-w-lg flex-col px-4 pb-24 pt-[max(1rem,env(safe-area-inset-top))]"
  >
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
              </span>
            </li>
          </ul>
          <p v-else class="text-sm text-slate-500">Nada na agenda hoje.</p>
        </div>
      </section>

      <button
        type="button"
        class="fixed bottom-[max(1.25rem,env(safe-area-inset-bottom))] right-4 z-20 flex h-14 w-14 items-center justify-center rounded-full bg-sky-600 text-2xl font-light text-white shadow-lg shadow-sky-900/50 active:bg-sky-700"
        aria-label="Adicionar item ou tarefa"
        @click="openFab"
      >
        +
      </button>

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