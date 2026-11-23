import { onMounted, onUnmounted, ref, type Ref } from "vue";

export function usePullRefresh(
  onRefresh: () => Promise<void>,
  opts?: { disabled?: Ref<boolean> }
) {
  const pullY = ref(0);
  const pulling = ref(false);
  let startY = 0;
  let busy = false;

  const THRESHOLD = 72;

  function onTouchStart(e: TouchEvent) {
    if (opts?.disabled?.value || busy) return;
    if (window.scrollY > 0) return;
    startY = e.touches[0]?.clientY ?? 0;
    pulling.value = true;
  }

  function onTouchMove(e: TouchEvent) {
    if (!pulling.value) return;
    const y = e.touches[0]?.clientY ?? 0;
    pullY.value = Math.max(0, Math.min(120, y - startY));
  }

  async function onTouchEnd() {
    if (!pulling.value) return;
    pulling.value = false;
    if (pullY.value >= THRESHOLD) {
      busy = true;
      try {
        await onRefresh();
      } finally {
        busy = false;
      }
    }
    pullY.value = 0;
  }

  onMounted(() => {
    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", onTouchEnd);
  });

  onUnmounted(() => {
    window.removeEventListener("touchstart", onTouchStart);
    window.removeEventListener("touchmove", onTouchMove);
    window.removeEventListener("touchend", onTouchEnd);
  });

  return { pullY, pulling };
}