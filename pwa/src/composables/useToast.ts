import { ref } from "vue";

const message = ref("");
let hideTimer: ReturnType<typeof setTimeout> | null = null;

export function useToast() {
  function showToast(text: string, ms = 2200) {
    message.value = text;
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      message.value = "";
      hideTimer = null;
    }, ms);
  }

  return { toastMessage: message, showToast };
}