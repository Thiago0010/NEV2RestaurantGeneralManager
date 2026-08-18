import React, { useState } from 'react';
import { Bell, ArrowLeft, Utensils, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function CustomerPreview({ restaurant, tableNumber }) {
  const [called, setCalled] = useState(false);
  return (
    <div className="mx-auto w-full max-w-[340px]">
      <div className="rounded-[2rem] border-4 border-secondary bg-background p-3 shadow-xl">
        <div className="overflow-hidden rounded-[1.5rem] bg-card">
          <div className="flex items-center justify-between gap-2 border-b border-border bg-secondary/50 px-4 py-3">
            <ArrowLeft className="h-4 w-4 text-muted-foreground" />
            <div className="text-center">
              <p className="font-heading text-sm font-semibold leading-tight">{restaurant?.name || 'Restaurante'}</p>
              <p className="text-[11px] text-muted-foreground">Mesa {tableNumber}</p>
            </div>
            <Utensils className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="space-y-3 p-4">
            <p className="text-xs text-muted-foreground">Prévia da tela do cliente</p>
            <div className="rounded-xl border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
              Cardápio digital do estabelecimento…
            </div>
            {called ? (
              <div className="flex items-start gap-2 rounded-xl border border-success/30 bg-success/15 px-4 py-3 text-sm text-success">
                <Check className="mt-0.5 h-4 w-4 shrink-0" />
                <span>Garçom a caminho! Em instantes alguém atenderá a Mesa {tableNumber}.</span>
              </div>
            ) : (
              <Button onClick={() => setCalled(true)} className="w-full">
                <Bell className="h-4 w-4" /> Chamar garçom
              </Button>
            )}
            {called && (
              <button onClick={() => setCalled(false)} className="w-full text-center text-xs text-muted-foreground underline">
                simular novamente
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}