import React, { useEffect, useState } from 'react';
import { api } from '@/lib/restaurant-context';
import { useRestaurant, userRestaurantId } from '@/lib/restaurant-context';
import { Loader2, QrCode, Copy, Printer, Download, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose
} from '@/components/ui/dialog';
import CustomerPreview from '@/components/CustumerPreview';

const QR_BASE = 'https://api.qrserver.com/v1/create-qr-code/';

function publicUrl(slug, tableNumber) {
  const origin = window.location.origin;
  return `${origin}/r/${slug}/table/${tableNumber}`;
}
function qrImg(url, size = 240) {
  return `${QR_BASE}?size=${size}x${size}&margin=8&data=${encodeURIComponent(url)}`;
}

export default function QRCodes() {
  const { user, restaurant } = useRestaurant();
  const rid = userRestaurantId(user);
  const { toast } = useToast();
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState(null);

  const load = async () => {
      setTables(await api.Table.filter({ restaurant_id: rid }, 'number', 500));
      setLoading(false);
    };
  useEffect(() => { if (rid) load(); /* eslint-disable-next-line */ }, [rid]);

  const copy = async (url) => {
    await navigator.clipboard.writeText(url);
    toast({ title: 'Link copiado' });
  };

  const printAll = () => {
    const w = window.open('', '_blank');
    const cards = tables.map((t) => {
      const url = publicUrl(restaurant.slug, t.number);
      return `<div style="page-break-inside:avoid;border:1px solid #ddd;border-radius:16px;padding:24px;text-align:center;margin:12px;">
        <h2 style="font-family:Georgia,serif;margin:0 0 4px;">${restaurant.name}</h2>
        <p style="color:#666;margin:0 0 16px;">Mesa ${t.number}</p>
        <img src="${qrImg(url, 300)}" width="240" height="240" />
        <p style="color:#888;margin-top:16px;font-size:13px;">Incline a câmera para escanear</p>
      </div>`;
    }).join('');
    w.document.write(`<html><head><title>QR Codes — ${restaurant.name}</title></head><body style="font-family:sans-serif;max-width:800px;margin:auto;padding:24px;">${cards}</body></html>`);
    w.document.close();
    setTimeout(() => w.print(), 500);
  };

  if (loading) return <div className="grid h-full place-items-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-3xl font-semibold">QR Codes</h1>
          <p className="text-sm text-muted-foreground">Um QR por mesa. Dinâmico — sempre aponta para o cardápio atual.</p>
        </div>
        {tables.length > 0 && <Button onClick={printAll}><Printer className="h-4 w-4" /> Imprimir todos</Button>}
      </div>

      {tables.length === 0 ? (
        <div className="surface-card grid h-48 place-items-center text-sm text-muted-foreground">Crie mesas primeiro para gerar os QR Codes.</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {tables.map((t) => {
            const url = publicUrl(restaurant.slug, t.number);
            return (
              <div key={t.id} className="surface-card p-5 text-center">
                <div className="mx-auto inline-flex rounded-xl bg-white p-2">
                  <img src={qrImg(url, 240)} width={168} height={168} alt={`QR Mesa ${t.number}`} />
                </div>
                <p className="mt-3 font-heading text-lg font-semibold">Mesa {t.number}</p>
                <p className="truncate text-xs text-muted-foreground">{url}</p>
                <div className="mt-3 flex flex-wrap justify-center gap-2">
                  <Button size="sm" variant="secondary" onClick={() => setPreview(t)}><Eye className="h-3.5 w-3.5" /> Prévia</Button>
                  <Button size="sm" variant="ghost" onClick={() => copy(url)}><Copy className="h-3.5 w-3.5" /> Copiar</Button>
                  <a href={qrImg(url, 600)} download={`qr-mesa-${t.number}.png`}>
                    <Button size="sm" variant="outline"><Download className="h-3.5 w-3.5" /> PNG</Button>
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={!!preview} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Prévia do cliente — Mesa {preview?.number}</DialogTitle></DialogHeader>
          <CustomerPreview restaurant={restaurant} tableNumber={preview?.number} />
          <p className="text-center text-xs text-muted-foreground">Assim o cliente vê o botão de chamar o garçom ao escanear o QR da mesa.</p>
          <div className="flex justify-end">
            <DialogClose asChild><Button variant="outline">Fechar</Button></DialogClose>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}