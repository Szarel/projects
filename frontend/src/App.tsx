import { useEffect, useState } from "react";
import {
  fetchProperties,
  fetchGeoJson,
  Property,
  getToken,
  setToken,
  createProperty,
  uploadDocument,
  fetchPropertyFull,
  downloadDocument,
  deleteDocument,
} from "./api";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";

function App() {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [properties, setProperties] = useState<Property[]>([]);
  const [geojson, setGeojson] = useState<any>({ type: "FeatureCollection", features: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newProp, setNewProp] = useState({
    codigo: "",
    direccion_linea1: "",
    comuna: "",
    region: "",
    tipo: "casa",
    estado_actual: "disponible",
    valor_arriendo: undefined as number | undefined,
    valor_venta: undefined as number | undefined,
    fecha_publicacion: "",
    lat: undefined as number | undefined,
    lon: undefined as number | undefined,
  });
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docCategoria, setDocCategoria] = useState("escritura");
  const [selectedProp, setSelectedProp] = useState<string>("");
  const [showModal, setShowModal] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showDetail, setShowDetail] = useState(false);

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
  };

  const handleCreateProperty = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const payload = {
        ...newProp,
        valor_arriendo: newProp.valor_arriendo || undefined,
        valor_venta: newProp.valor_venta || undefined,
        fecha_publicacion: newProp.fecha_publicacion || undefined,
        lat: newProp.lat || undefined,
        lon: newProp.lon || undefined,
      } as any;
      const created = await createProperty(payload);
      setProperties((prev) => [created, ...prev]);
      const refreshedGeo = await fetchGeoJson();
      setGeojson(refreshedGeo);
      setSelectedProp(created.id);
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
      await uploadDocument(selectedProp, docFile, docCategoria);
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
    setDetailLoading(true);
    setError(null);
    try {
      const full = await fetchPropertyFull(id);
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
      setDetail(full);
    } catch (err: any) {
      setError("No se pudo eliminar el documento");
    }
  };

  const handleReplaceDocument = async (doc: any, file: File) => {
    if (!detailId) return;
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(detailId, file, doc.categoria, doc.entidad_tipo);
      const full = await fetchPropertyFull(detailId);
      setDetail(full);
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const extra = detail ? `: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` : "";
      setError(`No se pudo subir el documento${status ? ` (${status})` : ""}${extra}`);
    } finally {
      setUploading(false);
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
  if (loading) return <div className="page">Cargando...</div>;
  if (error) return <div className="page error">{error}</div>;

  return (
    <div className="layout">
      <header className="topbar">
        <span>SIGAP – Mapa de Propiedades</span>
        <div className="top-actions">
          <button onClick={() => setShowModal(true)}>Agregar propiedad</button>
          <button className="ghost" onClick={handleLogout}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <main className="dash-page">
        <Dashboard
          properties={properties}
          geojson={geojson}
          onSelectProperty={handleSelectProperty}
          onDemoSeed={handleDemoSeed}
          creating={creating}
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
                  <label>
                    Código
                    <input value={newProp.codigo} onChange={(e) => setNewProp({ ...newProp, codigo: e.target.value })} required />
                  </label>
                  <label>
                    Dirección
                    <input
                      value={newProp.direccion_linea1}
                      onChange={(e) => setNewProp({ ...newProp, direccion_linea1: e.target.value })}
                      required
                    />
                  </label>
                  <label>
                    Comuna
                    <input value={newProp.comuna} onChange={(e) => setNewProp({ ...newProp, comuna: e.target.value })} required />
                  </label>
                  <label>
                    Región
                    <input value={newProp.region} onChange={(e) => setNewProp({ ...newProp, region: e.target.value })} required />
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
                  <label>
                    Estado
                    <select
                      value={newProp.estado_actual}
                      onChange={(e) => setNewProp({ ...newProp, estado_actual: e.target.value })}
                    >
                      <option value="disponible">Disponible</option>
                      <option value="arrendada">Arrendada</option>
                      <option value="en_venta">En venta</option>
                      <option value="vendida">Vendida</option>
                      <option value="desocupada">Desocupada</option>
                      <option value="mantencion">Mantención</option>
                      <option value="litigio">Litigio</option>
                      <option value="inactiva">Inactiva</option>
                    </select>
                  </label>
                  <label>
                    Valor arriendo
                    <input
                      type="number"
                      value={newProp.valor_arriendo ?? ""}
                      onChange={(e) =>
                        setNewProp({ ...newProp, valor_arriendo: e.target.value ? Number(e.target.value) : undefined })
                      }
                    />
                  </label>
                  <label>
                    Valor venta
                    <input
                      type="number"
                      value={newProp.valor_venta ?? ""}
                      onChange={(e) =>
                        setNewProp({ ...newProp, valor_venta: e.target.value ? Number(e.target.value) : undefined })
                      }
                    />
                  </label>
                  <label>
                    Fecha publicación
                    <input
                      type="date"
                      value={newProp.fecha_publicacion}
                      onChange={(e) => setNewProp({ ...newProp, fecha_publicacion: e.target.value })}
                    />
                  </label>
                  <label>
                    Lat
                    <input
                      type="number"
                      step="0.000001"
                      value={newProp.lat ?? ""}
                      onChange={(e) => setNewProp({ ...newProp, lat: e.target.value ? Number(e.target.value) : undefined })}
                    />
                  </label>
                  <label>
                    Lon
                    <input
                      type="number"
                      step="0.000001"
                      value={newProp.lon ?? ""}
                      onChange={(e) => setNewProp({ ...newProp, lon: e.target.value ? Number(e.target.value) : undefined })}
                    />
                  </label>
                </div>
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
                          <div>
                            <div>{d.categoria} · {d.filename}</div>
                            <div className="muted">v{d.version}</div>
                          </div>
                          <div className="doc-actions">
                            <button type="button" className="link" onClick={() => handleOpenDocument(d.id, d.filename)}>
                              Abrir
                            </button>
                            <button type="button" className="link" onClick={() => handleDeleteDocument(d.id)}>
                              Eliminar
                            </button>
                            <label className="link">
                              Reemplazar
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
    </div>
  );
}

export default App;
