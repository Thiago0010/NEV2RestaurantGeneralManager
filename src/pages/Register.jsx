import React, { useState, useMemo, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/AuthContext";
import { useRestaurant } from "@/lib/restaurant-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  UserPlus,
  Mail,
  Lock,
  Loader2,
  AlertCircle,
  CheckCircle,
  Shield,
  Building2,
} from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import { useToast } from "@/components/ui/use-toast";
import { slugify } from "@/lib/format";
import { extractErrorMessage } from "@/lib/error";
import { motion, AnimatePresence } from "framer-motion";
import { usePasswordStrength, useToggleVisibility } from "@/hooks/usePasswordStrength";

const ACCENTS = ['#e07a3c', '#c9a227', '#b85c3a', '#7a8c5a', '#9b6b4e', '#3a7a8c'];

const TextareaField = React.memo(({
  label,
  id,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  rows = 2,
  className = "",
}) => (
  <div className="space-y-2">
    <Label htmlFor={id}>{label}</Label>
    <FieldWrapper error={error}>
      <Textarea
        id={id}
        rows={rows}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        className={`focus-visible-ring ${className}`}
      />
    </FieldWrapper>
  </div>
));

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

const StrengthMeter = React.memo(({ score, label }) => {
  if (!score && score !== 0) return null;
  const colors = ["bg-transparent", "bg-red-500", "bg-yellow-500", "bg-yellow-400", "bg-green-500"];
  return (
    <div className="mt-2 space-y-1" role="progressbar" aria-valuenow={score} aria-valuemin={0} aria-valuemax={4} aria-label={`Força da senha: ${label}`}>
      <div className="flex gap-1 h-1.5">
        {[1, 2, 3, 4].map((i) => (
          <motion.div
            key={i}
            className={`strength-meter flex-1 rounded-full ${i <= score ? colors[score] : "bg-border"}`}
            initial={{ width: 0 }}
            animate={{ width: i <= score ? `${(100 / 4) * i}%` : 0 }}
            transition={{ duration: 0.3, delay: i * 0.05, type: "spring", stiffness: 300 }}
          />
        ))}
      </div>
      <p className="text-xs text-muted-foreground flex items-center gap-1">
        <Shield className="w-3 h-3" style={{ color: colors[score] || "inherit" }} />
        {label}
      </p>
    </div>
  );
});

const FormField = React.memo(({
  label,
  id,
  name,
  type = "text",
  autoComplete,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  disabled,
  required,
  minLength,
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
          name={name}
          type={type}
          autoComplete={autoComplete}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          className={`pl-10 h-12 ${className} focus-visible-ring`}
          required={required}
          disabled={disabled}
          minLength={minLength}
          aria-invalid={ariaInvalid}
        />
      </div>
    </FieldWrapper>
  </div>
));

export default function Register() {
  const { register, checkUserAuth } = useAuth();
  const { reload: reloadRestaurant } = useRestaurant();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    name: '',
    phone: '',
    address: '',
    welcome_message: '',
    accent_color: '#e07a3c',
    slug: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [touched, setTouched] = useState({});

  const [showPassword, togglePassword] = useToggleVisibility(false);

  const { score, label } = usePasswordStrength(form.password);

  const passwordMatch = form.password && form.confirmPassword && form.password === form.confirmPassword;
  const passwordMismatch = form.confirmPassword && form.password !== form.confirmPassword;

  const validateField = useCallback((name, value) => {
    switch (name) {
      case 'fullName':
        return value && value.trim().length < 2 ? 'Nome muito curto' : '';
      case 'email':
        return value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? 'E-mail inválido' : '';
      case 'password':
        return value && value.length < 6 ? 'Mínimo 6 caracteres' : '';
      case 'confirmPassword':
        return value && form.password !== value ? 'As senhas não conferem' : '';
      case 'name':
        return value && value.trim().length < 2 ? 'Nome muito curto' : '';
      case 'slug':
        return value && value.trim().length < 2 ? 'Código muito curto' : '';
      default:
        return '';
    }
  }, [form.password]);

  const handleBlur = useCallback((name) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
  }, []);

  const handleChange = useCallback((field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setError('');

    if (step === 1) {
      const errors = {};
      ['fullName', 'email', 'password', 'confirmPassword'].forEach(name => {
        const value = form[name];
        const err = validateField(name, value);
        if (err) errors[name] = err;
      });

      if (Object.keys(errors).length > 0) {
        setError(Object.values(errors)[0]);
        return;
      }

      setSubmitting(true);
      try {
        await register(form.email, form.password, form.fullName.trim(), '', '', '123');
        setSuccess(true);
        setStep(2);
        toast({ title: 'Conta criada com sucesso!', description: 'Agora configure seu estabelecimento.' });
      } catch (err) {
        const errMsg = err?.message || err?.detail || String(err);
        if (err.status === 400 && (errMsg.toLowerCase().includes('already'))) {
          setError('Este e-mail já está cadastrado. Faça login ou use outro e-mail.');
        } else {
          setError(errMsg || 'Erro ao criar conta. Tente novamente.');
        }
      } finally {
        setSubmitting(false);
      }
    } else {
      const errors = {};
      ['name', 'slug'].forEach(name => {
        const value = form[name];
        const err = validateField(name, value);
        if (err) errors[name] = err;
      });

      if (Object.keys(errors).length > 0) {
        setError(Object.values(errors)[0]);
        return;
      }

      setSubmitting(true);
      let registrationTimeoutId;
      try {
        const restaurantSlug = form.slug || slugify(form.name.trim());

        const controller = new AbortController();
        registrationTimeoutId = setTimeout(() => controller.abort(), 30000);

        const response = await fetch(`${import.meta.env.VITE_API_URL || '/api/v1'}/restaurant/onboarding`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({
            name: form.name.trim(),
            slug: restaurantSlug,
            phone: form.phone,
            address: form.address,
            welcome_message: form.welcome_message,
            accent_color: form.accent_color,
            currency: 'R$',
            service_tax_percent: 10.0
          }),
          signal: controller.signal
        });

        clearTimeout(registrationTimeoutId);

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || `HTTP ${response.status}`);
        }

        // Refresh BOTH the auth state and the restaurant provider state
        // so AppLayout (which reads from useRestaurant) sees the new restaurant_id.
        await Promise.all([
          checkUserAuth().catch(() => {}),
          reloadRestaurant(),
        ]);

        toast({ title: 'Estabelecimento criado', description: 'Bem-vindo ao seu painel.' });
        navigate('/', { replace: true });
      } catch (err) {
        clearTimeout(registrationTimeoutId);
        const errMsg = err?.message || err?.detail || String(err);
        if (err.name === 'AbortError' || errMsg.toLowerCase().includes('timeout')) {
          setError('A requisição demorou demais. O estabelecimento pode estar sendo criado. Tente recarregar a página.');
        } else if (errMsg.toLowerCase().includes('already') && errMsg.toLowerCase().includes('email')) {
          setError('Este e-mail já está cadastrado. Faça login ou use outro e-mail.');
        } else if (errMsg.toLowerCase().includes('slug')) {
          setError('Este nome de estabelecimento já está em uso. Tente outro nome.');
        } else if (errMsg.toLowerCase().includes('already has a restaurant')) {
          setError('Você já possui um estabelecimento cadastrado.');
        } else {
          setError(extractErrorMessage(err, 'Não foi possível criar o estabelecimento.'));
        }
      } finally {
        setSubmitting(false);
      }
    }
  }, [form, step, validateField, navigate, register, checkUserAuth, reloadRestaurant, toast]);

  const fullNameError = useMemo(() => touched.fullName ? validateField('fullName', form.fullName) : '', [touched.fullName, form.fullName, validateField]);
  const emailError = useMemo(() => touched.email ? validateField('email', form.email) : '', [touched.email, form.email, validateField]);
  const passwordError = useMemo(() => touched.password ? validateField('password', form.password) : '', [touched.password, form.password, validateField]);
  const confirmPasswordError = useMemo(() => touched.confirmPassword ? validateField('confirmPassword', form.confirmPassword) : '', [touched.confirmPassword, form.confirmPassword, validateField]);
  const nameError = useMemo(() => touched.name ? validateField('name', form.name) : '', [touched.name, form.name, validateField]);
  const slugError = useMemo(() => touched.slug ? validateField('slug', form.slug) : '', [touched.slug, form.slug, validateField]);

  return (
    <AuthLayout
      icon={UserPlus}
      title={step === 1 ? 'Criar conta' : 'Crie seu estabelecimento'}
      subtitle={step === 1 ? 'Preencha os dados para criar sua conta de administrador' : 'Este é o primeiro passo. Depois você configura mesas e cardápio.'}
      footer={
        <>
          {step === 1 ? 'Já tem conta?' : 'Voltar para conta?'}{' '}
          <Link
            to={step === 1 ? '/login' : '#'}
            onClick={step === 2 ? (e) => { e.preventDefault(); setStep(1); setSuccess(false); } : undefined}
            className="text-primary font-medium hover:underline"
          >
            {step === 1 ? 'Entrar' : 'Voltar'}
          </Link>
        </>
      }
    >
      <AnimatePresence mode="popLayout">
        {success && step === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-4 p-3 rounded-lg bg-green-500/10 text-green-500 text-sm flex items-center gap-2"
            role="status"
          >
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            Conta criada! Configure seu estabelecimento abaixo.
          </motion.div>
        )}
      </AnimatePresence>

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
            <span>{error}</span>
            {/login/.test(error) && (
              <Link to="/login" className="underline font-medium ml-1">Faça login</Link>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className={`flex items-center gap-2 ${step >= 1 ? 'text-primary' : 'text-muted-foreground'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-primary text-primary-foreground' : 'bg-secondary'}`}>
              {step >= 1 ? <CheckCircle className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
            </div>
            <span className="text-sm font-medium hidden sm:block">Conta</span>
          </div>
          <div className={`hidden sm:block flex-1 h-0.5 ${step >= 2 ? 'bg-primary' : 'bg-border'}`} />
          <div className={`flex items-center gap-2 ${step >= 2 ? 'text-primary' : 'text-muted-foreground'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-primary text-primary-foreground' : 'bg-secondary'}`}>
              {step >= 2 ? <CheckCircle className="w-4 h-4" /> : <Building2 className="w-4 h-4" />}
            </div>
            <span className="text-sm font-medium hidden sm:block">Estabelecimento</span>
          </div>
        </div>

        {step === 1 && (
          <>
            <FormField
              label="Nome completo"
              id="fullName"
              name="fullName"
              autoComplete="name"
              placeholder="Seu nome"
              value={form.fullName}
              onChange={(e) => handleChange('fullName', e.target.value)}
              onBlur={() => handleBlur('fullName')}
              error={fullNameError}
              disabled={submitting}
              required
              icon={UserPlus}
              ariaInvalid={touched.fullName && fullNameError ? 'true' : 'false'}
            />

            <FormField
              label="E-mail"
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="seu@email.com"
              value={form.email}
              onChange={(e) => handleChange('email', e.target.value)}
              onBlur={() => handleBlur('email')}
              error={emailError}
              disabled={submitting}
              required
              icon={Mail}
              ariaInvalid={touched.email && emailError ? 'true' : 'false'}
            />

            <FormField
              label="Senha"
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Crie uma senha"
              value={form.password}
              onChange={(e) => handleChange('password', e.target.value)}
              onBlur={() => handleBlur('password')}
              error={passwordError}
              disabled={submitting}
              required
              minLength={6}
              icon={Lock}
              className="pr-12"
              ariaInvalid={touched.password && passwordError ? 'true' : 'false'}
            />
            <StrengthMeter score={score} label={label} />
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Shield className="w-3 h-3" />
              Mínimo 6 caracteres. Use maiúsculas, números e símbolos para mais segurança.
            </p>

            <FormField
              label="Confirmar senha"
              id="confirmPassword"
              name="confirmPassword"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Confirme sua senha"
              value={form.confirmPassword}
              onChange={(e) => handleChange('confirmPassword', e.target.value)}
              onBlur={() => handleBlur('confirmPassword')}
              error={confirmPasswordError}
              disabled={submitting}
              required
              icon={Lock}
              className={`pr-12 ${passwordMatch ? 'input-valid' : passwordMismatch ? 'input-invalid' : ''}`}
              ariaInvalid={touched.confirmPassword && confirmPasswordError ? 'true' : 'false'}
            />
            {form.password && form.confirmPassword && (
              <p className={`text-xs flex items-center gap-1 ${passwordMatch ? 'text-green-500' : 'text-destructive'}`}>
                {passwordMatch ? (
                  <><CheckCircle className="w-3 h-3" /> As senhas conferem</>
                ) : (
                  <><AlertCircle className="w-3 h-3" /> As senhas não conferem</>
                )}
              </p>
            )}

            <Button
              type="submit"
              disabled={submitting}
              className="w-full h-12 font-medium rounded-xl focus-visible-ring"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" aria-hidden="true" />
                  Criando conta...
                </>
              ) : (
                'Continuar para estabelecimento'
              )}
            </Button>
          </>
        )}

        {step === 2 && (
          <>
            <FormField
              label="Nome do estabelecimento"
              id="name"
              value={form.name}
              onChange={(e) => handleChange('name', e.target.value)}
              onBlur={() => handleBlur('name')}
              error={nameError}
              placeholder="Espeto & Brasa"
            />

            <FormField
              label="Código do estabelecimento"
              id="slug"
              value={form.slug}
              onChange={(e) => handleChange('slug', e.target.value)}
              onBlur={() => handleBlur('slug')}
              error={slugError}
              placeholder="espeto-brasa"
            />
            {form.slug && <p className="text-xs text-muted-foreground">URL pública: /r/{form.slug}</p>}

            <FormField
              label="Telefone"
              id="phone"
              value={form.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              placeholder="(11) 99999-9999"
            />

            <div className="space-y-2">
              <Label>Cor de destaque</Label>
              <div className="flex gap-2 pt-1.5">
                {ACCENTS.map((c) => (
                  <button
                    type="button"
                    key={c}
                    onClick={() => handleChange('accent_color', c)}
                    className={`h-7 w-7 rounded-full border-2 transition ${form.accent_color === c ? 'border-foreground' : 'border-transparent'}`}
                    style={{ background: c }}
                  />
                ))}
              </div>
            </div>

            <FormField
              label="Endereço"
              id="address"
              value={form.address}
              onChange={(e) => handleChange('address', e.target.value)}
              placeholder="Rua, número, cidade"
            />

            <TextareaField
              label="Mensagem de boas-vindas (cliente QR)"
              id="welcome"
              value={form.welcome_message}
              onChange={(e) => handleChange('welcome_message', e.target.value)}
              placeholder="Bem-vindo! Escaneie e faça seu pedido."
              rows={2}
            />

            <Button
              type="submit"
              disabled={submitting}
              className="w-full h-12 font-medium rounded-xl focus-visible-ring"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" aria-hidden="true" />
                  Criando estabelecimento...
                </>
              ) : (
                'Criar estabelecimento e entrar'
              )}
            </Button>
          </>
        )}
      </form>
    </AuthLayout>
  );
}