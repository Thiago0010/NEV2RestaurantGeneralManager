import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { slugify } from '@/lib/format';
import { extractErrorMessage } from '@/lib/error';
import { Flame, Loader2, AlertCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { motion, AnimatePresence } from 'framer-motion';

const ACCENTS = ['#e07a3c', '#c9a227', '#b85c3a', '#7a8c5a', '#9b6b4e', '#3a7a8c'];

// FieldWrapper as a separate memoized component
const FieldWrapper = React.memo(({ children, error, className = '' }) => (
  <div className={className}>
    {children}
    <AnimatePresence mode="popLayout">
      {error && (
        <motion.p
          initial={{ opacity: 0, height: 0, y: -4 }}
          animate={{ opacity: 1, height: 'auto', y: 0 }}
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
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  className = "",
}) => (
  <div className="space-y-2">
    <Label htmlFor={id}>{label}</Label>
    <FieldWrapper error={error}>
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        className={`h-12 ${className} focus-visible-ring`}
      />
    </FieldWrapper>
  </div>
));

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

export default function Onboarding() {
  const { user, reload, loading } = useRestaurant();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [form, setForm] = useState({
    name: '',
    phone: '',
    address: '',
    welcome_message: '',
    accent_color: '#e07a3c',
    slug: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const slug = useMemo(() => slugify(form.slug || form.name), [form.slug, form.name]);

  const validateField = useCallback((name, value) => {
    switch (name) {
      case 'name':
        return value && value.trim().length < 2 ? 'Nome muito curto' : '';
      case 'slug':
        return value && value.trim().length < 2 ? 'Código muito curto' : '';
      default:
        return '';
    }
  }, []);

  const handleChange = useCallback((field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleNameChange = useCallback((e) => handleChange('name', e.target.value), [handleChange]);
  const handleSlugChange = useCallback((e) => handleChange('slug', e.target.value), [handleChange]);
  const handlePhoneChange = useCallback((e) => handleChange('phone', e.target.value), [handleChange]);
  const handleAddressChange = useCallback((e) => handleChange('address', e.target.value), [handleChange]);
  const handleWelcomeChange = useCallback((e) => handleChange('welcome_message', e.target.value), [handleChange]);

  const submit = useCallback(async (e) => {
      e.preventDefault();
      setError('');

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
          try {
            const restaurantSlug = slug || slugify(form.name.trim());

            // Call the new onboarding endpoint with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
         
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
                currency: "R$",
                service_tax_percent: 10.0
              }),
              signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
              const data = await response.json().catch(() => ({}));
              throw new Error(data.detail || `HTTP ${response.status}`);
            }

            const restaurant = await response.json();

                        await reload();
                        toast({
                          title: 'Estabelecimento criado',
                          description: 'Você ganhou 7 dias de trial grátis. Escolha um plano quando quiser.',
                        });
                        // Send the user to /settings so they can pick a plan
                        // (or stay on trial). The Settings page already lists
                        // the catalogue, so no need for a separate redirect.
                        navigate('/settings', { replace: true });
          } catch (err) {
            clearTimeout(timeoutId);
            const errMsg = err?.message || err?.detail || String(err);
            if (err.name === 'AbortError' || errMsg.includes('timeout') || errMsg.includes('Timeout')) {
              setError('A requisição demorou demais. O estabelecimento pode estar sendo criado. Tente recarregar a página.');
            } else if (errMsg.includes('already') || errMsg.includes('Email already')) {
              setError('Este e-mail já está cadastrado. <a href="/login" className="underline font-medium">Faça login</a> ou use outro e-mail.');
            } else if (errMsg.includes('Slug') || errMsg.includes('slug')) {
              setError('Este nome de estabelecimento já está em uso. Tente outro nome.');
            } else if (errMsg.includes('already has a restaurant')) {
              setError('Você já possui um estabelecimento cadastrado.');
            } else {
              setError(extractErrorMessage(err, 'Não foi possível criar o estabelecimento.'));
            }
          } finally {
            setSubmitting(false);
          }
    }, [form, slug, validateField, navigate, reload, toast, handleChange]);

  // Memoize error states
  const nameError = useMemo(() => validateField('name', form.name), [form.name, validateField]);
  const slugError = useMemo(() => validateField('slug', form.slug), [form.slug, validateField]);

  if (loading) return <div className="grid h-screen place-items-center"><Loader2 className="h-7 w-7 animate-spin-smooth text-primary" /></div>;
  if (userRestaurantId(user)) return <Navigate to="/" replace />;

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="relative hidden lg:flex flex-col justify-between p-12 bg-sidebar border-r border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary/15 border border-primary/30">
            <Flame className="h-6 w-6 text-primary" />
          </div>
          <span className="font-heading text-xl font-semibold">Restaurant OS</span>
        </div>
        <div className="space-y-4">
          <h1 className="font-heading text-4xl font-semibold leading-tight">
            O sistema operacional do seu restaurante.
          </h1>
          <p className="text-muted-foreground text-lg max-w-md">
            Mesas, cardápio, pedidos, cozinha e QR Code — tudo conectado, em tempo real, só para o seu estabelecimento.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">Multi-tenant · Isolamento de dados · Tempo real</p>
      </div>

      <div className="flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md space-y-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 lg:hidden">
              <Flame className="h-6 w-6 text-primary" />
              <span className="font-heading text-xl font-semibold">Restaurant OS</span>
            </div>
            <h2 className="font-heading text-2xl font-semibold">Crie seu estabelecimento</h2>
            <p className="text-sm text-muted-foreground">Este é o primeiro passo. Depois você configura mesas e cardápio.</p>
          </div>

          <AnimatePresence mode="popLayout">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2"
                role="alert"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span dangerouslySetInnerHTML={{ __html: error }} />
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={submit} className="space-y-4">
            <AnimatePresence mode="popLayout">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-2"
              >
                <FormField
                  label="Nome do estabelecimento"
                  id="name"
                  value={form.name}
                  onChange={handleNameChange}
                  onBlur={() => handleNameChange({ target: { value: form.name } })}
                  error={nameError}
                  placeholder="Espeto & Brasa"
                />
              </motion.div>
            </AnimatePresence>

            <AnimatePresence mode="popLayout">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: 0.05 }}
                className="space-y-2"
              >
                <FormField
                  label="Código do estabelecimento"
                  id="slug"
                  value={form.slug}
                  onChange={handleSlugChange}
                  onBlur={() => handleSlugChange({ target: { value: form.slug } })}
                  error={slugError}
                  placeholder="espeto-brasa"
                />
                {slug && <p className="text-xs text-muted-foreground">URL pública: /r/{slug}</p>}
              </motion.div>
            </AnimatePresence>

            <AnimatePresence mode="popLayout">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: 0.1 }}
                className="space-y-2"
              >
                <FormField
                  label="Telefone"
                  id="phone"
                  value={form.phone}
                  onChange={handlePhoneChange}
                  placeholder="(11) 99999-9999"
                />
              </motion.div>
            </AnimatePresence>

            <AnimatePresence mode="popLayout">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: 0.15 }}
                className="space-y-2"
              >
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
              </motion.div>
            </AnimatePresence>

            <AnimatePresence mode="popLayout">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: 0.2 }}
                className="space-y-2"
              >
                <FormField
                  label="Endereço"
                  id="address"
                  value={form.address}
                  onChange={handleAddressChange}
                  placeholder="Rua, número, cidade"
                />
              </motion.div>
            </AnimatePresence>

            <AnimatePresence mode="popLayout">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: 0.25 }}
                className="space-y-2"
              >
                <TextareaField
                  label="Mensagem de boas-vindas (cliente QR)"
                  id="welcome"
                  value={form.welcome_message}
                  onChange={handleWelcomeChange}
                  placeholder="Bem-vindo! Escaneie e faça seu pedido."
                  rows={2}
                />
              </motion.div>
            </AnimatePresence>

            <AnimatePresence mode="popLayout">
              <motion.button
                type="submit"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: 0.3 }}
                disabled={submitting}
                className="w-full h-12 font-medium rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 focus-visible-ring transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin-smooth" aria-hidden="true" />
                    <span className="flex items-center">Criando estabelecimento...</span>
                  </>
                ) : (
                  'Criar estabelecimento'
                )}
              </motion.button>
            </AnimatePresence>
          </form>
        </div>
      </div>
    </div>
  );
}