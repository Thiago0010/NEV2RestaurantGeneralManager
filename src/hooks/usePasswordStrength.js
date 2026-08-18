import { useState, useMemo } from 'react';

export function useToggleVisibility(initial = false) {
  const [visible, setVisible] = useState(initial);
  const toggle = () => setVisible(v => !v);
  return [visible, toggle, setVisible];
}

export function usePasswordStrength(password) {
  return useMemo(() => {
    if (!password) return { score: 0, label: '', checks: {} };

    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[^A-Za-z0-9]/.test(password),
    };

    const passed = Object.values(checks).filter(Boolean).length;
    let score = 0;
    if (password.length >= 6) score = 1;
    if (password.length >= 8 && passed >= 2) score = 2;
    if (password.length >= 10 && passed >= 3) score = 3;
    if (password.length >= 12 && passed >= 4) score = 4;

    const labels = ['Muito fraca', 'Fraca', 'Média', 'Forte', 'Muito forte'];
    const label = labels[score] || '';

    return { score, label, checks, passed };
  }, [password]);
}