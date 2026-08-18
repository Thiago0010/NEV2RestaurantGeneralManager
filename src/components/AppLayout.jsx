import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate, Navigate } from 'react-router-dom';
import { useRestaurant, userRestaurantId, api } from '@/lib/restaurant-context';
import {
  LayoutDashboard, LayoutGrid, ChefHat, Bell, QrCode, BarChart3, Users,
  Settings, LogOut, Utensils, Flame, Loader2
} from 'lucide-react';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['owner', 'manager'] },
  { to: '/tables', label: 'Mesas', icon: LayoutGrid, roles: ['owner', 'manager', 'waiter'] },
  { to: '/menu', label: 'Cardápio', icon: Utensils, roles: ['owner', 'manager'] },
  { to: '/kitchen', label: 'Cozinha', icon: ChefHat, roles: ['owner', 'manager', 'kitchen'] },
  { to: '/waiter', label: 'Garçom', icon: Bell, roles: ['owner', 'manager', 'waiter'] },
  { to: '/qr-codes', label: 'QR Codes', icon: QrCode, roles: ['owner', 'manager'] },
  { to: '/reports', label: 'Relatórios', icon: BarChart3, roles: ['owner', 'manager'] },
  { to: '/employees', label: 'Funcionários', icon: Users, roles: ['owner'] },
  { to: '/settings', label: 'Configurações', icon: Settings, roles: ['owner', 'manager'] },
];

function NavItem({ item, onNavigate }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      onClick={onNavigate}
      className={({ isActive }) =>
        `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
          isActive
            ? 'bg-primary/15 text-primary border border-primary/30'
            : 'text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent border border-transparent'
        }`
      }
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      <span>{item.label}</span>
    </NavLink>
  );
}

function Sidebar({ role, restaurant, onNavigate }) {
  const navigate = useNavigate();
  const items = nav.filter((n) => n.roles.includes(role));
  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex items-center gap-3 px-5 py-5 border-b border-sidebar-border">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/15 border border-primary/30">
          <Flame className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="truncate font-heading text-base font-semibold leading-tight text-foreground">
            {restaurant?.name || 'Restaurant OS'}
          </p>
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Restaurant OS</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1.5 overflow-y-auto p-3">
        {items.map((item) => (
          <NavItem key={item.to} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-3">
              <button
                onClick={async () => { await api.auth.logout(); window.location.href = '/login'; }}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
              >
                <LogOut className="h-[18px] w-[18px]" />
                Sair
              </button>
            </div>
    </aside>
  );
}

function Shell() {
  const { user, restaurant, loading } = useRestaurant();
  const [mobileOpen, setMobileOpen] = useState(false);
  const role = user?.role || 'owner';

  if (loading) {
    return (
      <div className="grid h-screen place-items-center">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
      </div>
    );
  }

  if (!userRestaurantId(user)) {
    return <Navigate to="/onboarding" replace />;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="hidden md:block h-full">
        <Sidebar role={role} restaurant={restaurant} />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 h-full">
            <Sidebar role={role} restaurant={restaurant} onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-border bg-card/60 px-4 py-3 backdrop-blur md:px-8">
          <button
            className="rounded-lg p-2 text-muted-foreground hover:bg-accent md:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <LayoutGrid className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="hidden sm:inline">Operando</span>
            <span className="font-medium text-foreground">{restaurant?.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium capitalize text-secondary-foreground">
              {role === 'owner' ? 'dono' : role === 'manager' ? 'gerente' : role === 'waiter' ? 'garçom' : 'cozinha'}
            </span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function AppLayout() {
  return <Shell />;
}