(() => {
  const getDocId = () => {
    const parts = window.location.pathname.split("/").filter(Boolean);
    if (parts.length >= 2 && parts[0] === "doc") {
      return parts[1];
    }
    return parts[parts.length - 1] || "";
  };

  const resolveBackendBase = () => {
    const explicit = window.CODOC_BACKEND_BASE_URL;
    if (explicit) return String(explicit).replace(/\/$/, "");

    const { protocol, hostname, port } = window.location;
    if (port === "3000") return `${protocol}//${hostname}:8000`;
    return `${protocol}//${hostname}${port ? `:${port}` : ""}`;
  };

  const exportPdf = () => {
    const docId = getDocId();
    if (!docId) return;
    const base = resolveBackendBase();
    const url = `${base}/__export/pdf?doc_id=${encodeURIComponent(docId)}&_ts=${Date.now()}`;
    window.open(url, "_blank", "noopener");
  };

  window.codocExportPdf = exportPdf;
})();
