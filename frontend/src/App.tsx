import { useEffect, useMemo, useState } from "react";
import {
  fetchProperties,
  fetchGeoJson,
  Property,
  getToken,
  setToken,
  createProperty,
  deleteProperty,
  uploadDocument,
  fetchPropertyFull,
  downloadDocument,
  deleteDocument,
  replaceDocument,
} from "./api";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";

function App() {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [properties, setProperties] = useState<Property[]>([]);
  const [geojson, setGeojson] = useState<any>({ type: "FeatureCollection", features: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [prefetching, setPrefetching] = useState(false);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newProp, setNewProp] = useState({
    direccion_linea1: "",
    tipo: "casa",
    codigo: "",
  });
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docCategoria, setDocCategoria] = useState("escritura");
  const [selectedProp, setSelectedProp] = useState<string>("");
  const [arrendatarioId, setArrendatarioId] = useState<string>("");
  const [propietarioId, setPropietarioId] = useState<string>("");
  const [showModal, setShowModal] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [detailsCache, setDetailsCache] = useState<Record<string, any>>({});
  const defaultLat = -33.45;
  const defaultLon = -70.66;
  const [toast, setToast] = useState<string | null>(null);
  const [filters, setFilters] = useState({ estado: "todos", tipo: "todos", comuna: "" });
  const [showFilters, setShowFilters] = useState(false);
  const [alertsData, setAlertsData] = useState({
    vencidos: 0,
    porVencer: 0,
    sinContrato: 0,
    cobranzaAtrasada: 0,
    docsIncompletos: 0,
  });
  const [nowScl, setNowScl] = useState<Date>(new Date());

  useEffect(() => {
    const id = setInterval(() => setNowScl(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const nowLabel = useMemo(() => {
    try {
      return new Intl.DateTimeFormat("es-CL", {
        timeZone: "America/Santiago",
        dateStyle: "medium",
        timeStyle: "medium",
      }).format(nowScl);
    } catch {
      return nowScl.toISOString();
    }
  }, [nowScl]);

  const filteredProperties = useMemo(() => {
    return properties.filter((p) => {
      const matchEstado = filters.estado === "todos" || (p.estado_actual || "").toLowerCase() === filters.estado;
      const matchTipo = filters.tipo === "todos" || (p.tipo || "").toLowerCase() === filters.tipo;
      const matchComuna = filters.comuna ? (p.comuna || "").toLowerCase().includes(filters.comuna.toLowerCase()) : true;
      return matchEstado && matchTipo && matchComuna;
    });
  }, [filters, properties]);

  const filteredGeojson = useMemo(() => {
    const allowed = new Set(filteredProperties.map((p) => p.id));
    const nextFeatures = (geojson.features || []).filter((f: any) => allowed.has(f.properties.id));
    return { ...geojson, features: nextFeatures };
  }, [filteredProperties, geojson]);

  const computeAlerts = (props: Property[], cache: Record<string, any>) => {
    const tzNow = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Santiago" }));
    const addDays = (date: Date, days: number) => new Date(date.getTime() + days * 24 * 60 * 60 * 1000);

    let vencidos = 0;
    let porVencer = 0;
    let sinContrato = 0;
    let cobranzaAtrasada = 0;
    let docsIncompletos = 0;

    for (const p of props) {
      const detail = cache[p.id];
      const contract = detail?.current_contract;
      const charges = detail?.charges || [];
      const docs = detail?.documents || [];

      if (!contract && (p.estado_actual || "").toLowerCase() === "disponible") sinContrato += 1;

      if (contract?.fecha_fin) {
        const fin = new Date(contract.fecha_fin);
        if (!Number.isNaN(fin.getTime())) {
          if (fin < tzNow) vencidos += 1;
          else if (fin <= addDays(tzNow, 30)) porVencer += 1;
        }
      }

      const hasDocs = docs.length > 0;
      if (!hasDocs) docsIncompletos += 1;

      const lateCharge = charges.find((c: any) => {
        const venc = c.fecha_vencimiento ? new Date(c.fecha_vencimiento) : null;
        const isLate = venc ? venc < tzNow : false;
        const estado = (c.estado || "").toLowerCase();
        return estado === "atraso" || estado === "pendiente" && isLate;
      });
      if (lateCharge) cobranzaAtrasada += 1;
    }

    return { vencidos, porVencer, sinContrato, cobranzaAtrasada, docsIncompletos };
  };

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2200);
    return () => clearTimeout(t);
  }, [toast]);

  async function geocodeAddress(address: string): Promise<{
    lat: number;
    lon: number;
    comuna?: string;
    region?: string;
  } | null> {
    if (!address.trim()) return null;
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=1&q=${encodeURIComponent(address + ", Chile")}`;
      const resp = await fetch(url, { headers: { Accept: "application/json" } });
      if (!resp.ok) return null;
      const data = await resp.json();
      if (!data?.length) return null;
      const item = data[0];
      const lat = parseFloat(item.lat);
      const lon = parseFloat(item.lon);
      const comuna = item.address?.city || item.address?.town || item.address?.village || item.address?.county;
      const region = item.address?.state;
      return { lat, lon, comuna, region };
    } catch {
      return null;
    }
  }

  const inferComunaFromAddress = (address: string) => {
    const lower = address.toLowerCase();
    if (lower.includes("ñuñoa") || lower.includes("nunoa")) return "Ñuñoa";
    return null;
  };

  async function prefetchDetails(props: Property[]) {
    if (!props.length) return;
    setPrefetching(true);
    try {
      await Promise.allSettled(
        props.map(async (p) => {
          if (detailsCache[p.id]) return;
          const full = await fetchPropertyFull(p.id);
          setDetailsCache((prev) => (prev[p.id] ? prev : { ...prev, [p.id]: full }));
        })
      );
    } finally {
      setPrefetching(false);
    }
  }

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    const load = async () => {
      setLoading(true);
      try {
        const [props, geo] = await Promise.all([fetchProperties(), fetchGeoJson()]);
        setProperties(props);
        setGeojson(geo);
        prefetchDetails(props);
      } catch (e: any) {
        if (e?.response?.status === 401) {
          setToken(null);
          setTokenState(null);
          setError("Sesión expirada, vuelve a ingresar");
        } else {
          setError("No se pudo cargar la data");
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token]);

  useEffect(() => {
    const hydrateAlerts = async () => {
      if (!properties.length) {
        setAlertsData({ vencidos: 0, porVencer: 0, sinContrato: 0, cobranzaAtrasada: 0, docsIncompletos: 0 });
        return;
      }
      const copyCache: Record<string, any> = { ...detailsCache };
      for (const p of properties) {
        if (copyCache[p.id]) continue;
        try {
          const full = await fetchPropertyFull(p.id);
          copyCache[p.id] = full;
          setDetailsCache((prev) => ({ ...prev, [p.id]: full }));
        } catch {
          /* ignore single failures */
        }
      }
      setAlertsData(computeAlerts(properties, copyCache));
    };
    hydrateAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [properties]);

  useEffect(() => {
    const populateParties = async () => {
      if (!selectedProp) {
        setArrendatarioId("");
        setPropietarioId("");
        return;
      }

      const cached = detailsCache[selectedProp];
      if (cached?.current_contract) {
        setArrendatarioId(cached.current_contract.arrendatario?.id || "");
        setPropietarioId(cached.current_contract.propietario?.id || "");
        return;
      }

      try {
        const full = await fetchPropertyFull(selectedProp);
        setDetailsCache((prev) => ({ ...prev, [selectedProp]: full }));
        if (full?.current_contract) {
          setArrendatarioId(full.current_contract.arrendatario?.id || "");
          setPropietarioId(full.current_contract.propietario?.id || "");
        }
      } catch (err) {
        // Best-effort prefill; ignore errors
      }
    };

    void populateParties();
  }, [selectedProp, detailsCache]);

  const handleLogin = (tok: string) => {
    setToken(tok);
    setTokenState(tok);
    setError(null);
  };

  const handleLogout = () => {
    setToken(null);
    setTokenState(null);
    setProperties([]);
    setGeojson({ type: "FeatureCollection", features: [] });
    setDetailsCache({});
  };

  const handleCreateProperty = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      if (!newProp.direccion_linea1.trim()) {
        setError("Ingresa una dirección");
        return;
      }

      const geo = await geocodeAddress(newProp.direccion_linea1);
      const fallbackComuna = inferComunaFromAddress(newProp.direccion_linea1);
      const geoComuna = geo?.comuna?.toLowerCase().includes("provincia de santiago") && fallbackComuna ? null : geo?.comuna;
      const generatedCode = newProp.codigo?.trim() || `PRP-${Date.now()}`;
      const payload = {
        codigo: generatedCode,
        direccion_linea1: newProp.direccion_linea1,
        comuna: fallbackComuna || geoComuna || "Sin comuna",
        region: geo?.region || "Sin región",
        tipo: newProp.tipo,
        estado_actual: "disponible",
        valor_arriendo: undefined,
        valor_venta: undefined,
        fecha_publicacion: undefined,
        lat: geo?.lat ?? defaultLat,
        lon: geo?.lon ?? defaultLon,
      } as any;
      const created = await createProperty(payload);
      setProperties((prev) => [created, ...prev]);
      const refreshedGeo = await fetchGeoJson();
      setGeojson(refreshedGeo);
      setSelectedProp(created.id);
      setToast("Propiedad creada y ubicada en el mapa");
      setNewProp({ direccion_linea1: "", tipo: "casa", codigo: "" });
    } catch (err: any) {
      setError("No se pudo crear la propiedad");
    } finally {
      setCreating(false);
    }
  };

  const handleUploadDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docFile || !selectedProp) return;
    setUploading(true);
    setError(null);
    try {
      if (docCategoria === "contrato_arriendo") {
        if (!arrendatarioId || !propietarioId) {
          setError("Debes indicar arrendatario y propietario para el contrato");
          setUploading(false);
          return;
        }
      }

      await uploadDocument(selectedProp, docFile, docCategoria, "propiedad", {
        arrendatario_id: arrendatarioId || undefined,
        propietario_id: propietarioId || undefined,
      });
      const full = await fetchPropertyFull(selectedProp);
      setDetailsCache((prev) => ({ ...prev, [selectedProp]: full }));
      if (detailId === selectedProp) setDetail(full);
      setToast("Documento subido");
      setDocCategoria("escritura");
      setArrendatarioId("");
      setPropietarioId("");
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const extra = detail ? `: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : "";
      setError(`No se pudo subir el documento${status ? ` (${status})` : ""}${extra}`);
    } finally {
      setUploading(false);
      setDocFile(null);
    }
  };

  const handleSelectProperty = async (id: string) => {
    setSelectedProp(id);
    setDetailId(id);
    setShowDetail(true);
    setError(null);
    const cached = detailsCache[id];
    if (cached) {
      setDetail(cached);
      setDetailLoading(false);
    } else {
      setDetailLoading(true);
    }
    try {
      const full = await fetchPropertyFull(id);
      setDetailsCache((prev) => ({ ...prev, [id]: full }));
      setDetail(full);
    } catch (err: any) {
      setError("No se pudo cargar la ficha");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleOpenDocument = async (docId: string, filename: string) => {
    try {
      const blob = await downloadDocument(docId);
      const url = URL.createObjectURL(blob);
      const newWindow = window.open(url, "_blank");
      if (!newWindow) {
        setError("No se pudo abrir la pestaña");
      }
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const extra = detail ? `: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : "";
      setError(`No se pudo abrir el documento${status ? ` (${status})` : ""}${extra}`);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!detailId) return;
    if (!confirm("¿Eliminar este documento?")) return;
    try {
      await deleteDocument(docId);
      const full = await fetchPropertyFull(detailId);
      setDetailsCache((prev) => ({ ...prev, [detailId]: full }));
      setDetail(full);
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const extra = detail ? `: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : "";
      setError(`No se pudo eliminar el documento${status ? ` (${status})` : ""}${extra}`);
    }
  };

  const handleReplaceDocument = async (doc: any, file: File) => {
    if (!detailId) return;
    setUploading(true);
    setError(null);
    try {
      await replaceDocument(doc.id, file, doc.categoria);
      const full = await fetchPropertyFull(detailId);
      setDetailsCache((prev) => ({ ...prev, [detailId]: full }));
      setDetail(full);
      setToast("Documento reemplazado");
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const extra = detail ? `: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : "";
      setError(`No se pudo reemplazar el documento${status ? ` (${status})` : ""}${extra}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteProperty = async (id: string) => {
    if (!confirm("¿Eliminar esta propiedad?")) return;
    setError(null);
    try {
      await deleteProperty(id);
      setProperties((prev) => prev.filter((p) => p.id !== id));
      const refreshedGeo = await fetchGeoJson();
      setGeojson(refreshedGeo);
      if (detailId === id) {
        setShowDetail(false);
        setDetail(null);
        setDetailId(null);
      }
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const extra = detail ? `: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : "";
      setError(`No se pudo eliminar la propiedad${status ? ` (${status})` : ""}${extra}`);
    }
  };

  const handleDemoSeed = async () => {
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      const samples = [
        {
          codigo: "CASA-001",
          direccion_linea1: "Av. Apoquindo 1234",
          comuna: "Las Condes",
          region: "Metropolitana",
          tipo: "casa",
          estado_actual: "disponible",
          valor_arriendo: 1200000,
          valor_venta: 250000000,
          fecha_publicacion: "2024-01-10",
          lat: -33.411,
          lon: -70.567,
        },
        {
          codigo: "DEP-045",
          direccion_linea1: "General Holley 2407",
          comuna: "Providencia",
          region: "Metropolitana",
          tipo: "departamento",
          estado_actual: "arrendada",
          valor_arriendo: 800000,
          valor_venta: 180000000,
          fecha_publicacion: "2024-02-02",
          lat: -33.424,
          lon: -70.612,
        },
        {
          codigo: "OFI-220",
          direccion_linea1: "Rosario Norte 555",
          comuna: "Las Condes",
          region: "Metropolitana",
          tipo: "oficina",
          estado_actual: "en_venta",
          valor_arriendo: undefined,
          valor_venta: 320000000,
          fecha_publicacion: "2024-03-12",
          lat: -33.406,
          lon: -70.569,
        },
      ];
      for (const s of samples) {
        try {
          await createProperty(s as any);
        } catch (_) {
          /* ignore duplicates */
        }
      }
      const [props, geo] = await Promise.all([fetchProperties(), fetchGeoJson()]);
      setProperties(props);
      setGeojson(geo);
    } catch (err: any) {
      setError("No se pudo cargar la demo");
    } finally {
      setCreating(false);
    }
  };

  if (!token) return <Login onSuccess={handleLogin} />;
  if (loading)
    return (
      <div className="loading-screen">
        <div className="spinner" aria-hidden="true" />
        <p>Preparando datos...</p>
      </div>
    );
  if (error) return <div className="page error">{error}</div>;

  return (
    <div className="layout">
      <header className="topbar">
        <div className="topbar-title">
          <span>SIGAP – Mapa de Propiedades</span>
          <span className="clock">{nowLabel} (Santiago)</span>
        </div>
        <div className="top-actions">
          {prefetching && <span className="prefetch-pill">Sincronizando datos…</span>}
          <button className="ghost" onClick={() => setShowFilters((v) => !v)}>
            {showFilters ? "Ocultar filtros" : "Mostrar filtros"}
          </button>
          <button onClick={() => setShowModal(true)}>Agregar propiedad</button>
          <button className="ghost" onClick={handleLogout}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <main className="dash-page">
        <Dashboard
          properties={filteredProperties}
          fullProperties={properties}
          geojson={filteredGeojson}
          onSelectProperty={handleSelectProperty}
          onDeleteProperty={handleDeleteProperty}
          filters={filters}
          onChangeFilters={setFilters}
          alertsData={alertsData}
          showFilters={showFilters}
        />
      </main>

      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Agregar propiedad y documentos</h3>
              <button className="ghost" onClick={() => setShowModal(false)}>
                Cerrar
              </button>
            </div>
            <div className="forms">
              <form className="card" onSubmit={handleCreateProperty}>
                <div className="form-row">
                  <h3>Nueva propiedad</h3>
                  <button type="submit" disabled={creating}>
                    {creating ? "Guardando..." : "Guardar"}
                  </button>
                </div>
                <div className="grid">
                  <label className="full">
                    Dirección (se geolocaliza automáticamente)
                    <input
                      value={newProp.direccion_linea1}
                      onChange={(e) => setNewProp({ ...newProp, direccion_linea1: e.target.value })}
                      required
                    />
                  </label>
                  <label>
                    Tipo
                    <select value={newProp.tipo} onChange={(e) => setNewProp({ ...newProp, tipo: e.target.value })}>
                      <option value="casa">Casa</option>
                      <option value="departamento">Departamento</option>
                      <option value="oficina">Oficina</option>
                      <option value="local">Local</option>
                      <option value="terreno">Terreno</option>
                    </select>
                  </label>
                </div>
                <p className="muted">Usaremos la dirección para obtener coordenadas y ponerla en el mapa automáticamente.</p>
              </form>

              <form className="card" onSubmit={handleUploadDoc}>
                <div className="form-row">
                  <h3>Documentos</h3>
                  <button type="submit" disabled={uploading || !docFile || !selectedProp}>
                    {uploading ? "Subiendo..." : "Subir"}
                  </button>
                </div>
                <label>
                  Propiedad
                  <select value={selectedProp} onChange={(e) => setSelectedProp(e.target.value)} required>
                    <option value="">Selecciona</option>
                    {properties.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.codigo} - {p.direccion_linea1}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Categoría
                  <select value={docCategoria} onChange={(e) => setDocCategoria(e.target.value)}>
                    <option value="escritura">Escritura</option>
                    <option value="contrato_arriendo">Contrato arriendo</option>
                    <option value="inventario">Inventario</option>
                    <option value="factura">Factura</option>
                    <option value="recibo">Recibo</option>
                  </select>
                </label>
                {docCategoria === "contrato_arriendo" && (
                  <>
                    <label>
                      Arrendatario (UUID)
                      <input
                        value={arrendatarioId}
                        onChange={(e) => setArrendatarioId(e.target.value)}
                        placeholder="ID de arrendatario"
                        required
                      />
                    </label>
                    <label>
                      Propietario (UUID)
                      <input
                        value={propietarioId}
                        onChange={(e) => setPropietarioId(e.target.value)}
                        placeholder="ID de propietario"
                        required
                      />
                    </label>
                    <p className="muted">Si la propiedad ya tiene contrato, prellenamos los IDs; puedes reemplazarlos.</p>
                  </>
                )}
                <label>
                  Archivo
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                    onChange={(e) => setDocFile(e.target.files?.[0] || null)}
                  />
                </label>
              </form>
            </div>
          </div>
        </div>
      )}

      {showDetail && (
        <div className="modal-backdrop" onClick={() => setShowDetail(false)}>
          <div className="modal detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Ficha de propiedad</h3>
                {detail?.property && (
                  <p className="muted">{detail.property.codigo} · {detail.property.direccion_linea1}</p>
                )}
              </div>
              <button className="ghost" onClick={() => setShowDetail(false)}>Cerrar</button>
            </div>

            {detailLoading && <div>Cargando ficha...</div>}
            {!detailLoading && detail?.property && (
              <div className="detail-grid">
                <div className="card">
                  <h4>Resumen</h4>
                  <p>{detail.property.direccion_linea1}</p>
                  <p>{detail.property.comuna}, {detail.property.region}</p>
                  <p>Estado: {detail.property.estado_actual}</p>
                  {detail.property.valor_arriendo && <p>Arriendo: ${detail.property.valor_arriendo}</p>}
                  {detail.property.valor_venta && <p>Venta: ${detail.property.valor_venta}</p>}
                  {detail.current_contract && (
                    <p>Contrato vigente: vence {detail.current_contract.fecha_fin}</p>
                  )}
                </div>

                <div className="card">
                  <h4>Contrato vigente</h4>
                  {detail.current_contract ? (
                    <div className="stack">
                      <span>Arrendatario: {detail.current_contract.arrendatario.nombre}</span>
                      <span>Renta: {detail.current_contract.renta_mensual} {detail.current_contract.moneda}</span>
                      <span>Pago cada día {detail.current_contract.dia_pago ?? "-"}</span>
                      <span>Periodo: {detail.current_contract.fecha_inicio} → {detail.current_contract.fecha_fin}</span>
                    </div>
                  ) : (
                    <p className="muted">Sin contrato vigente</p>
                  )}
                </div>

                <div className="card">
                  <h4>Historial de estados</h4>
                  {detail.state_history?.length ? (
                    <ul>
                      {detail.state_history.map((h: any) => (
                        <li key={`${h.estado}-${h.fecha_inicio}`}>
                          {h.estado} · {h.fecha_inicio} {h.fecha_fin ? `→ ${h.fecha_fin}` : ""}
                          {h.motivo && ` (${h.motivo})`}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">Sin historial</p>
                  )}
                </div>

                <div className="card">
                  <h4>Documentos</h4>
                  {detail.documents?.length ? (
                    <div className="doc-list">
                      {detail.documents.map((d: any) => (
                        <div key={d.id} className="doc-row">
                          <div className="doc-meta">
                            <div className="doc-name">{d.categoria} · {d.filename}</div>
                            <div className="muted">v{d.version}</div>
                          </div>
                          <div className="doc-actions">
                            <button type="button" className="icon-btn" title="Abrir" onClick={() => handleOpenDocument(d.id, d.filename)}>
                              ↗
                            </button>
                            <button type="button" className="icon-btn danger" title="Eliminar" onClick={() => handleDeleteDocument(d.id)}>
                              ✕
                            </button>
                            <label className="icon-btn" title="Reemplazar">
                              ⟳
                              <input
                                type="file"
                                className="sr-only"
                                accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                                onChange={(e) => {
                                  const file = e.target.files?.[0];
                                  if (file) {
                                    handleReplaceDocument(d, file);
                                    e.target.value = "";
                                  }
                                }}
                              />
                            </label>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">Sin documentos</p>
                  )}
                </div>

                <div className="card">
                  <h4>Contratos</h4>
                  {detail.contracts?.length ? (
                    <ul>
                      {detail.contracts.map((c: any) => (
                        <li key={c.id}>{c.estado} · {c.fecha_inicio} → {c.fecha_fin} · {c.arrendatario.nombre}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">Sin contratos</p>
                  )}
                </div>

                <div className="card">
                  <h4>Cobranzas</h4>
                  {detail.charges?.length ? (
                    <ul>
                      {detail.charges.map((c: any) => (
                        <li key={c.id}>{c.periodo}: {c.estado} vence {c.fecha_vencimiento}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">Sin cobranzas</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {toast && (
        <div className="toast" role="status">
          <div className="toast-icon" aria-hidden="true">✓</div>
          <span>{toast}</span>
        </div>
      )}
    </div>
  );
}

export default App;
