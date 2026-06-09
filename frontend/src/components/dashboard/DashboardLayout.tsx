import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { LayoutDashboard, Scan, Signal, BarChart3, BookOpen, Shield, TrendingUp, LogOut } from 'lucide-react';

const navItems = [
  { to: '/scanner', icon: Scan, label: 'Scanner' },
  { to: '/signals', icon: Signal, label: 'Signals' },
  { to: '/positions', icon: BarChart3, label: 'Positions' },
  { to: '/backtest', icon: TrendingUp, label: 'Backtest' },
  { to: '/risk', icon: Shield, label: 'Risk' },
  { to: '/analytics', icon: LayoutDashboard, label: 'Analytics' },
  { to: '/journal', icon: BookOpen, label: 'Journal' },
];

export function DashboardLayout() {
  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex">
      <nav className="w-64 bg-gray-900 border-r border-gray-800 p-4 flex flex-col">
        <div className="mb-8">
          <h1 className="text-xl font-bold text-white">PerfectTrading</h1>
          <p className="text-xs text-gray-500">Futures Trading Platform</p>
        </div>
        <div className="flex-1 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg text-sm transition-colors mt-4"
        >
          <LogOut size={18} />
          Logout
        </button>
      </nav>
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
