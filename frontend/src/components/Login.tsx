import { useEffect, useRef, useState } from "react";
import { login, loginWithGoogle, signup } from "../api";

type Props = {
  onSuccess: (token: string) => void;
};

declare global {
  interface Window {
    google?: any;
  }
}

export default function Login({ onSuccess }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "signup">("login");
  const googleBtnRef = useRef<HTMLDivElement | null>(null);
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

  const handleGoogleCredential = async (response: any) => {
    const credential = response?.credential;
    if (!credential) {
      setError("No se recibió el token de Google");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const token = await loginWithGoogle(credential);
      onSuccess(token);
    } catch (err: any) {
      const status = err?.response?.status;
      setError(status === 401 ? "Token de Google inválido" : "Error con Google");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!googleClientId) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (!window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleCredential,
        ux_mode: "popup",
      });
      if (googleBtnRef.current) {
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: "outline",
          size: "large",
          shape: "pill",
          text: "continue_with",
        });
      }
    };
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, [googleClientId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "signup") {
        await signup(email, password, fullName || undefined);
        const token = await login(email, password);
        onSuccess(token);
      } else {
        const token = await login(email, password);
        onSuccess(token);
      }
    } catch (err: any) {
      const status = err?.response?.status;
      if (mode === "signup") {
        setError(status === 400 ? "Correo ya registrado" : "Error al registrar");
      } else {
        setError(status === 401 ? "Credenciales inválidas" : "Error al iniciar sesión");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <form className="card" onSubmit={handleSubmit}>
        <div className="auth-tabs">
          <button
            type="button"
            className={mode === "login" ? "auth-tab active" : "auth-tab"}
            onClick={() => setMode("login")}
          >
            Ingresar
          </button>
          <button
            type="button"
            className={mode === "signup" ? "auth-tab active" : "auth-tab"}
            onClick={() => setMode("signup")}
          >
            Registrarse
          </button>
        </div>
        <h2>{mode === "login" ? "Ingresar a SIGAP" : "Crear cuenta"}</h2>
        {mode === "signup" && (
          <label>
            Nombre
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Tu nombre"
            />
          </label>
        )}
        <label>
          Correo
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="usuario@dominio.cl"
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="••••••••"
          />
        </label>
        {error && <div className="error-msg">{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? (mode === "login" ? "Validando..." : "Creando...") : mode === "login" ? "Ingresar" : "Crear cuenta"}
        </button>
        {googleClientId && <div className="google-sep">o continúa con</div>}
        {googleClientId && <div ref={googleBtnRef} className="google-btn-slot" />}
      </form>
    </div>
  );
}
