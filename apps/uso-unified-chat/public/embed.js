/**
 * USO Unified Chat Embed Script
 * Usage: <script src="https://your-domain/embed.js" data-partner-id="PARTNER_UUID"></script>
 * Or: <div id="uso-chat-embed" data-partner-id="PARTNER_UUID"></div>
 */
(function () {
  const script = document.currentScript;
  const partnerId = script?.getAttribute("data-partner-id") || "";
  const baseUrl =
    script?.src?.replace(/\/embed\.js.*$/, "") ||
    (typeof window !== "undefined" && window.location.origin) ||
    "";

  if (!baseUrl) {
    console.warn("[USO Chat] Could not determine base URL");
    return;
  }

  const params = new URLSearchParams();
  if (partnerId) params.set("partner_id", partnerId);
  if (typeof window !== "undefined" && window.location?.origin) {
    params.set("parent_origin", window.location.origin);
  }
  const embedUrl = params.toString()
    ? `${baseUrl}/embed?${params.toString()}`
    : `${baseUrl}/embed`;

  const container = document.getElementById("uso-chat-embed") || document.body;
  const iframe = document.createElement("iframe");
  iframe.src = embedUrl;
  iframe.title = "USO Chat";
  iframe.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 400px;
    height: 600px;
    max-width: calc(100vw - 40px);
    max-height: calc(100vh - 40px);
    border: none;
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.15);
    z-index: 999999;
  `;

  container.appendChild(iframe);
})();
