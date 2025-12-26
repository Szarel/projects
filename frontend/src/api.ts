import axios from "axios";

const TOKEN_KEY = "sigap_token";

const api = axios.create({
  // Usar API relativa para que frontend y backend convivan bajo el mismo dominio (rewrites Firebase/Cloud Run)
  baseURL: import.meta.env.VITE_API_URL || "/api",
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY) || import.meta.env.VITE_API_TOKEN || null;
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export async function login(username: string, password: string): Promise<string> {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const { data } = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  setToken(data.access_token);
  return data.access_token as string;
}

export type Property = {
  id: string;
  codigo: string;
  direccion_linea1: string;
  comuna: string;
  region: string;
  tipo: string;
  estado_actual: string;
  valor_arriendo?: number;
  valor_venta?: number;
  lat?: number;
  lon?: number;
};

export async function fetchProperties(): Promise<Property[]> {
  const { data } = await api.get("/properties");
  return data;
}

export async function fetchGeoJson(): Promise<any> {
  const { data } = await api.get("/properties/geojson");
  return data;
}

export async function fetchPropertyFull(propertyId: string): Promise<any> {
  const { data } = await api.get(`/properties/${propertyId}/full`);
  return data;
}

export async function createProperty(payload: Omit<Property, "id">): Promise<Property> {
  const { data } = await api.post("/properties", payload);
  return data;
}

export async function downloadDocument(documentId: string): Promise<Blob> {
  const { data } = await api.get(`/documents/${documentId}/download`, { responseType: "blob" });
  return data as Blob;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/documents/${documentId}`);
}

export async function uploadDocument(
  entidad_id: string,
  file: File,
  categoria: string,
  entidad_tipo = "propiedad"
): Promise<void> {
  const formData = new FormData();
  formData.append("entidad_tipo", entidad_tipo);
  formData.append("entidad_id", entidad_id);
  formData.append("categoria", categoria);
  formData.append("file", file);
  await api.post("/documents", formData);
}
