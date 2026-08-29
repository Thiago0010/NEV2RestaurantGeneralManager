// API Client for [NEV]2 Restaurant Management System Backend
//
// Pick the API base URL with these rules, in order:
//   1. If VITE_API_URL is set AND looks absolute (http/https), honor it as-is.
//      That's the override for split-host deployments (backend on a different
//      domain, or absolute API URLs baked at build time by CI).
//   2. Otherwise, return a RELATIVE "/api/v1/" base. This is what makes the
//      customer QR flow actually work: when a phone on the restaurant Wi-Fi
//      scans the code, the page is served from the LAN IP (e.g.
//      http://192.168.0.10:5173), and the relative URL keeps the fetch on
//      that same host. Vite's dev proxy and the production nginx.conf both
//      rewrite /api -> backend, so the request lands on the right server
//      without the user having to know the backend's address.
//   3. Fall back to the loopback default (127.0.0.1:8000) only when running
//      in a non-browser environment (Node tests, scripts) that didn't set
//      the variable.
const RAW_API_URL = import.meta.env.VITE_API_URL || '';
const IS_BROWSER = typeof window !== 'undefined' && typeof window.location !== 'undefined';
const IS_ABSOLUTE = /^https?:\/\//i.test(RAW_API_URL);
const API_BASE_URL = IS_ABSOLUTE
  ? RAW_API_URL
  : (IS_BROWSER ? '/api/v1/' : 'http://127.0.0.1:8000/');
const DEFAULT_TIMEOUT = 15000; // 15 seconds

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Builds a query string from a params object, supporting arrays
// (e.g. { status: ['received', 'preparing'] } -> status=received&status=preparing)
// without converting values via `toString()` (which would yield `[object Object]`
// when an object accidentally slips into a list).
function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (Array.isArray(value)) {
      value.forEach(v => {
        if (v === undefined || v === null) return;
        if (typeof v === 'object') return; // ignore unexpected objects
        search.append(key, String(v));
      });
    } else if (typeof value === 'object') {
      return; // ignore unexpected nested objects
    } else {
      search.append(key, String(value));
    }
  });
  return search.toString();
}

let on402Callback = null;

export function set402Handler(callback) {
  on402Callback = callback;
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  // Add auth token if available
  const token = localStorage.getItem('access_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const config = {
    ...options,
    headers,
  };
  
  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }
  
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT);
  config.signal = controller.signal;
  
  try {
    const response = await fetch(url, config);
    clearTimeout(timeoutId);
    
    if (response.status === 204) {
      return null;
    }
    
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
      // Handle 402 Payment Required - billing required
      if (response.status === 402 && on402Callback) {
        on402Callback(data);
      }
      
      throw new ApiError(
        data.detail || `HTTP ${response.status}`,
        response.status,
        data
      );
    }
    
    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof ApiError) {
      throw error;
    }
    if (error.name === 'AbortError' || error.name === 'TimeoutError') {
      throw new ApiError('Request timeout - server not responding', 408, {});
    }
    throw new ApiError(error.message || 'Network error', 0, {});
  }
}

// Auth endpoints
export const authApi = {
  login: (email, password) => request('/auth/login', {
    method: 'POST',
    body: { email, password },
  }),

  register: async (email, password, fullName, restaurantName = "", restaurantSlug = "", secretKey = "") => request('/auth/register', {
    method: 'POST',
    body: {
      email,
      password,
      full_name: fullName,
      restaurant_name: restaurantName || undefined,
      restaurant_slug: restaurantSlug || undefined,
      secret_key: secretKey || undefined
    },
  }),

  getMe: () => request('/auth/me'),

  updateMe: (data) => request('/auth/me', {
    method: 'PUT',
    body: data,
  }),

  createStaff: (email, password, fullName, role) => request('/auth/staff', {
    method: 'POST',
    body: { email, password, full_name: fullName, role },
  }),

  changePassword: (currentPassword, newPassword) => request('/auth/me/password', {
    method: 'PUT',
    body: { current_password: currentPassword, new_password: newPassword },
  }),

  resetPasswordRequest: (email) => request('/auth/forgot-password', {
    method: 'POST',
    body: { email },
  }),

  resetPassword: ({ resetToken, newPassword }) => request('/auth/reset-password', {
    method: 'POST',
    body: { token: resetToken, new_password: newPassword },
  }),
};

// Restaurant endpoints
export const restaurantApi = {
  getMine: () => request('/restaurant/me'),
  
  updateMine: (data) => request('/restaurant/me', {
    method: 'PUT',
    body: data,
  }),
  
  getPublic: (slug) => request(`/public/restaurant/${slug}`),
  
  getByQr: (qrToken) => request(`/public/restaurant/qr/${qrToken}`),
};

// Category endpoints
export const categoryApi = {
  list: (params = {}) => {
    const query = buildQuery(params);
    return request(`/categories?${query}`);
  },
  
  get: (id) => request(`/categories/${id}`),
  
  create: (data) => request('/categories', {
    method: 'POST',
    body: data,
  }),
  
  update: (id, data) => request(`/categories/${id}`, {
    method: 'PUT',
    body: data,
  }),
  
  delete: (id) => request(`/categories/${id}`, {
    method: 'DELETE',
  }),
};

// Product endpoints
export const productApi = {
  list: (params = {}) => {
    const query = buildQuery(params);
    return request(`/products?${query}`);
  },
  
  get: (id) => request(`/products/${id}`),
  
  create: (data) => request('/products', {
    method: 'POST',
    body: data,
  }),
  
  update: (id, data) => request(`/products/${id}`, {
    method: 'PUT',
    body: data,
  }),
  
  toggleField: (id, field) => request(`/products/${id}/toggle/${field}`, {
    method: 'PATCH',
  }),
  
  delete: (id) => request(`/products/${id}`, {
    method: 'DELETE',
  }),
};

// Table endpoints
export const tableApi = {
  list: (params = {}) => {
    const query = buildQuery(params);
    return request(`/tables?${query}`);
  },
  
  get: (id) => request(`/tables/${id}`),
  
  create: (data) => request('/tables', {
    method: 'POST',
    body: data,
  }),
  
  update: (id, data) => request(`/tables/${id}`, {
    method: 'PUT',
    body: data,
  }),
  
  delete: (id) => request(`/tables/${id}`, {
    method: 'DELETE',
  }),
  
  getQr: (id) => request(`/tables/${id}/qr`),
  
  getAllQr: () => request('/tables/qr/all'),
};

// Order endpoints
export const orderApi = {
  list: (params = {}) => {
    // Accept either a params object (legacy callers) or a pre-built query
    // string (used by `api.Order.filter`, which already handles arrays and
    // base44-style `$in` operators and serializes them into a raw query).
    const query = typeof params === 'string' ? params : buildQuery(params);
    return request(`/orders${query ? `?${query}` : ''}`);
  },
  
  getActive: () => request('/orders/active'),
  
  get: (id) => request(`/orders/${id}`),
  
  create: (data) => request('/orders', {
    method: 'POST',
    body: data,
  }),
  
  update: (id, data) => request(`/orders/${id}`, {
    method: 'PUT',
    body: data,
  }),
  
  addItems: (id, items) => request(`/orders/${id}/items`, {
    method: 'POST',
    body: items,
  }),
  
  deleteItem: (itemId) => request(`/orders/items/${itemId}`, {
    method: 'DELETE',
  }),
  
  // Public endpoints (no auth)
  createPublic: (restaurantId, data) => request(`/public/restaurant/${restaurantId}/orders`, {
    method: 'POST',
    body: data,
  }),
  
  getPublicActive: (restaurantId, tableId) => request(`/public/restaurant/${restaurantId}/orders/active?table_id=${tableId}`),
  
  addItemsPublic: (restaurantId, orderId, items) => request(`/public/restaurant/${restaurantId}/orders/${orderId}/items`, {
    method: 'POST',
    body: items,
  }),
};

// Employee endpoints
export const employeeApi = {
  list: (params = {}) => {
    const query = buildQuery(params);
    return request(`/employees?${query}`);
  },
  
  get: (id) => request(`/employees/${id}`),
  
  create: (data) => request('/employees', {
    method: 'POST',
    body: data,
  }),
  
  update: (id, data) => request(`/employees/${id}`, {
    method: 'PUT',
    body: data,
  }),
  
  toggleActive: (id) => request(`/employees/${id}/toggle-active`, {
    method: 'PATCH',
  }),
  
  delete: (id) => request(`/employees/${id}`, {
    method: 'DELETE',
  }),
};

// Service Call endpoints
export const serviceCallApi = {
  list: (params = {}) => {
    const query = buildQuery(params);
    return request(`/service-calls?${query}`);
  },
  
  getPending: () => request('/service-calls/pending'),
  
  create: (data) => request('/service-calls', {
    method: 'POST',
    body: data,
  }),
  
  update: (id, data) => request(`/service-calls/${id}`, {
    method: 'PUT',
    body: data,
  }),
  
  // Public endpoint (no auth)
  createPublic: (restaurantId, data) => request(`/public/restaurant/${restaurantId}/service-calls`, {
    method: 'POST',
    body: data,
  }),
};

// Public endpoints (no auth)
export const publicApi = {
  getCategories: (restaurantId) => request(`/public/restaurant/${restaurantId}/categories`),
  
  getProducts: (restaurantId, categoryId) => {
    const params = categoryId ? `?category_id=${categoryId}` : '';
    return request(`/public/restaurant/${restaurantId}/products${params}`);
  },
  
  getTable: (restaurantId, tableNumber) => request(`/public/restaurant/${restaurantId}/tables/${tableNumber}`),
};

export { ApiError, request };
export default {
  auth: authApi,
  restaurant: restaurantApi,
  category: categoryApi,
  product: productApi,
  table: tableApi,
  order: orderApi,
  employee: employeeApi,
  serviceCall: serviceCallApi,
  public: publicApi,
};