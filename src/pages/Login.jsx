import React, { useState, useMemo, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LogIn, Mail, Lock, Loader2, AlertCircle } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import { safeReturnTo } from "@/lib/authReturnTo";
import { motion, AnimatePresence } from "framer-motion";
import { usePasswordStrength } from "@/hooks/usePasswordStrength";

// FieldWrapper as a separate memoized component
const FieldWrapper = React.memo(({ children, error, className = "" }) => (
  <div className={className}>
    {children}
    <AnimatePresence mode="popLayout">
      {error && (
        <motion.p
          initial={{ opacity: 0, height: 0, y: -4 }}
          animate={{ opacity: 1, height: "auto", y: 0 }}
          exit={{ opacity: 0, height: 0, y: -4 }}
          className="text-xs text-destructive mt-1 flex items-center gap-1"
          role="alert"
        >
          <AlertCircle className="w-3 h-3 flex-shrink-0" />
          {error}
        </motion.p>
      )}
    </AnimatePresence>
  </div>
));

// FormField as a separate component to isolate re-renders
const FormField = React.memo(({
  label,
  id,
  type = "text",
  autoComplete,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  required,
  autoFocus,
  icon: Icon,
  className = "",
  ariaInvalid = "false"
}) => (
  <div className="space-y-2">
    <Label htmlFor={id}>{label}</Label>
    <FieldWrapper error={error}>
      <div className="relative">
        {Icon && <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />}
        <Input
          id={id}
          type={type}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          className={`pl-10 h-12 ${className} focus-visible-ring`}
          required={required}
          aria-invalid={ariaInvalid}
        />
      </div>
    </FieldWrapper>
  </div>
));

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState({});

  const [showPassword, setShowPassword] = useState(false);
  const { score, label } = usePasswordStrength(password);

  const returnTo = safeReturnTo();

  const validateField = useCallback((name, value) => {
    switch (name) {
      case "email":
        return value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? "E-mail inválido" : "";
      case "password":
        return value && value.length < 6 ? "Mínimo 6 caracteres" : "";
      default:
        return "";
    }
  }, []);

  const handleBlur = useCallback((name) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
  }, []);

  const handleEmailChange = useCallback((e) => setEmail(e.target.value), []);
  const handlePasswordChange = useCallback((e) => setPassword(e.target.value), []);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setError("");

    const errors = {};
    ["email", "password"].forEach((name) => {
      const value = name === "email" ? email : password;
      const err = validateField(name, value);
      if (err) errors[name] = err;
    });

    if (Object.keys(errors).length > 0) {
      setError(Object.values(errors)[0]);
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      // SPA navigation keeps state (toasts, query cache) intact
      navigate(returnTo, { replace: true });
    } catch (err) {
      setError(err.message || "E-mail ou senha inválidos");
    } finally {
      setLoading(false);
    }
  }, [email, password, validateField, returnTo, login, navigate]);

  // Memoize error states
  const emailError = useMemo(() => touched.email ? validateField("email", email) : "", [touched.email, email, validateField]);
  const passwordError = useMemo(() => touched.password ? validateField("password", password) : "", [touched.password, password, validateField]);

  return (
    <AuthLayout
      icon={LogIn}
      title="Bem-vindo de volta"
      subtitle="Entre na sua conta"
      footer={
        <>
          Não tem conta?{" "}
          <Link
            to={"/onboarding" + (returnTo !== "/" ? "?returnTo=" + encodeURIComponent(returnTo) : "")}
            className="text-primary font-medium hover:underline"
          >
            Criar estabelecimento
          </Link>
        </>
      }
    >
      <AnimatePresence mode="popLayout">
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2"
            role="alert"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField
          label="E-mail"
          id="email"
          type="email"
          autoComplete="email"
          autoFocus
          placeholder="seu@email.com"
          value={email}
          onChange={handleEmailChange}
          onBlur={() => handleBlur("email")}
          error={emailError}
          required
          icon={Mail}
          ariaInvalid={touched.email && emailError ? "true" : "false"}
        />

        <div>
          <div className="flex items-center justify-between">
            {/* <Label htmlFor="password">Senha</Label> */}
            <Link to="/forgot-password" className="text-xs text-primary hover:underline">
              Esqueci a senha
            </Link>
          </div>
          <FormField
            label="Senha"
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            placeholder="Sua senha"
            value={password}
            onChange={handlePasswordChange}
            onBlur={() => handleBlur("password")}
            error={passwordError}
            required
            icon={Lock}
            className="pr-12"
            ariaInvalid={touched.password && passwordError ? "true" : "false"}
          />
        </div>

        <Button
          type="submit"
          disabled={loading}
          className="w-full h-12 font-medium rounded-xl focus-visible-ring"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" aria-hidden="true" />
              Entrando...
            </>
          ) : (
            "Entrar"
          )}
        </Button>
      </form>
    </AuthLayout>
  );
}