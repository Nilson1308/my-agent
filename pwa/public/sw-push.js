/* Web Push — importado pelo Workbox (vite-plugin-pwa). */
self.addEventListener("push", (event) => {
  let title = "My Agent";
  let body = "Atualização";
  let tag = "my-agent";
  try {
    const data = event.data?.json();
    if (data?.title) title = data.title;
    if (data?.body) body = data.body;
    if (data?.tag) tag = data.tag;
  } catch {
    const text = event.data?.text();
    if (text) body = text;
  }
  event.waitUntil(
    self.registration.showNotification(title, { body, tag, icon: "/app/icon.svg" })
  );
});