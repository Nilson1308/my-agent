export function pickRecorderMime(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/aac",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];
  for (const t of candidates) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

export function filenameForBlobType(mime: string): string {
  const m = mime.toLowerCase();
  if (m.includes("mp4") || m.includes("aac") || m.includes("m4a")) return "voice.m4a";
  if (m.includes("ogg")) return "voice.ogg";
  return "voice.webm";
}

/** Finaliza MediaRecorder e devolve o blob (espera onstop + último dataavailable). */
export function finishMediaRecorder(
  recorder: MediaRecorder,
  chunks: Blob[],
  fallbackMime: string,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      recorder.stream.getTracks().forEach((t) => t.stop());
      const mime = recorder.mimeType || fallbackMime || "audio/webm";
      resolve(new Blob(chunks, { type: mime }));
    };
    recorder.onerror = () => {
      if (settled) return;
      settled = true;
      reject(new Error("Falha na gravação"));
    };
    recorder.onstop = done;
    try {
      recorder.requestData();
    } catch {
      /* nem todo navegador implementa */
    }
    if (recorder.state === "recording" || recorder.state === "paused") {
      recorder.stop();
    } else {
      done();
    }
  });
}