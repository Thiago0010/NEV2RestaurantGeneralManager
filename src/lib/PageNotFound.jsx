import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Flame, Home, ArrowLeft, ChefHat, Compass } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Footer from '@/components/Footer';

export default function PageNotFound() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      {/* Decorative gradient blobs */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-secondary/30 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6 py-12 text-center">
        {/* Brand mark */}
        <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15">
            <Flame className="h-4 w-4 text-primary" />
          </div>
          <span className="font-heading font-semibold text-foreground">[NEV]² Restaurant Manager</span>
        </div>

        {/* 404 number with chef hat */}
        <div className="relative">
          <h1 className="select-none bg-gradient-to-br from-primary to-primary/40 bg-clip-text font-heading text-[140px] font-bold leading-none text-transparent sm:text-[180px]">
            404
          </h1>
          <div className="absolute -right-2 top-2 rotate-12 rounded-full bg-secondary p-2 shadow-md sm:-right-6 sm:top-6">
            <ChefHat className="h-6 w-6 text-secondary-foreground" />
          </div>
        </div>

        {/* Message */}
        <h2 className="mt-4 font-heading text-2xl font-semibold sm:text-3xl">
          Página não encontrada
        </h2>
        <p className="mt-3 max-w-md text-sm text-muted-foreground sm:text-base">
          A cozinha não tem esse prato no cardápio. A rota
          <code className="mx-1.5 rounded-md border border-border bg-muted px-2 py-0.5 font-mono text-xs text-foreground">
            {path || '/'}
          </code>
          não existe ou foi movida.
        </p>

        {/* Quick links */}
        <div className="mt-8 grid w-full max-w-lg grid-cols-1 gap-3 sm:grid-cols-3">
          <Button onClick={() => navigate('/')} className="w-full">
            <Home className="h-4 w-4" /> Início
          </Button>
          <Button onClick={() => navigate(-1)} variant="secondary" className="w-full">
            <ArrowLeft className="h-4 w-4" /> Voltar
          </Button>
          <Button onClick={() => navigate('/menu')} variant="outline" className="w-full">
            <Compass className="h-4 w-4" /> Cardápio
          </Button>
        </div>

        {/* Fun easter egg */}
        <div className="mt-10 max-w-md rounded-2xl border border-dashed border-border bg-card/50 p-4 text-xs text-muted-foreground">
          <p>
            <span className="font-heading text-sm font-semibold text-foreground">Dica do chef:</span>{' '}
            se o cliente chegou aqui pelo QR Code, vale conferir se a mesa
            existe e se o slug do restaurante está correto.
          </p>
        </div>

        {/* Version line */}
        <p className="mt-10 text-[11px] uppercase tracking-wider text-muted-foreground">
          [NEV]² · v1.0.0
        </p>
      </div>
      <Footer />
    </div>
  );
}
