import React from 'react';
import { Flame } from 'lucide-react';

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-10 border-t border-border/60 py-5 text-center text-xs text-muted-foreground">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-center gap-1 px-4">
        <div className="flex items-center gap-1.5 text-foreground/80">
          <Flame className="h-3.5 w-3.5 text-primary" />
          <span className="font-medium">[NEV]²</span>
          <span className="text-muted-foreground">·</span>
          <span>Restaurant Management System</span>
          <span className="text-muted-foreground">·</span>
          <span className="font-mono">v1.0.0</span>
        </div>
        <p>
          © {year} [NEV]² · [NEV]²Thi_ii · [NEV]²Henriique__
        </p>
      </div>
    </footer>
  );
}
