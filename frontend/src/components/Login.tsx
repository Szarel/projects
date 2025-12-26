import { useEffect, useRef, useState } from "react";
import { login, loginWithGoogle } from "../api";

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      const token = await login(email, password);
      onSuccess(token);
    } catch (err: any) {
      const status = err?.response?.status;
      setError(status === 401 ? "Credenciales inválidas" : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <form className="card" onSubmit={handleSubmit}>
        <h2>Ingresar a SIGAP</h2>
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
          {loading ? "Validando..." : "Ingresar"}
        </button>
        {googleClientId && <div className="google-sep">o continúa con</div>}
        {googleClientId && <div ref={googleBtnRef} className="google-btn-slot" />}
      </form>
    </div>
  );
}
