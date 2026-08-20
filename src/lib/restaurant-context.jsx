// Restaurant Context - replaces Base44 restaurant context
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, restaurantApi, tableApi, categoryApi, productApi, orderApi, employeeApi, serviceCallApi } from '@/api/client';

const defaultContext = {
  user: null,
  restaurant: null,
  loading: false,
  reload: async () => {},
  setRestaurant: () => {},
  setUser: () => {},
};

const Ctx = createContext(defaultContext);

export function RestaurantProvider({ children }) {
  const [user, setUser] = useState(null);
  const [restaurant, setRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const user = await authApi.getMe();
      setUser(user);

      const rid = user?.restaurant_id || '';
      if (rid) {
        try {
          // Fetch restaurant data separately
          const restaurant = await restaurantApi.getMine();
          setRestaurant(restaurant);
        } catch (e) {
          // User authenticated but no restaurant yet (e.g. just registered, onboarding)
          setRestaurant(null);
        }
      } else {
        setRestaurant(null);
      }
    } catch (e) {
      setUser(null);
      setRestaurant(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Ctx.Provider value={{ user, restaurant, loading, reload: load, setRestaurant, setUser }}>
      {children}
    </Ctx.Provider>
  );
}

export const useRestaurant = () => {
  const context = useContext(Ctx);
  return context ?? defaultContext;
};

export function userRestaurantId(user) {
  return user?.restaurant_id || '';
}

export function userStaffRole(user) {
  return user?.role || 'owner';
}

// Helper: backend paginated responses -> flat array (keeps base44-like API)
async function listAsArray(promise) {
  const data = await promise;
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  return [];
}

// API service functions that replace base44.entities.*
export const api = {
  // Restaurant
  restaurant: {
    getMine: () => restaurantApi.getMine(),
    updateMine: (data) => restaurantApi.updateMine(data),
    getPublic: (slug) => restaurantApi.getPublic(slug),
    getByQr: (qrToken) => restaurantApi.getByQr(qrToken),
  },

  // Categories
  Category: {
    filter: (params, sort, limit) => {
      const query = new URLSearchParams();
      if (params?.restaurant_id) query.set('restaurant_id', params.restaurant_id);
      if (sort) query.set('sort', sort);
      if (limit) query.set('page_size', limit);
      return listAsArray(categoryApi.list(Object.fromEntries(query)));
    },
    create: (data) => categoryApi.create(data),
    update: (id, data) => categoryApi.update(id, data),
    delete: (id) => categoryApi.delete(id),
    bulkCreate: async (items) => {
      const results = [];
      for (const item of items) {
        results.push(await categoryApi.create(item));
      }
      return results;
    },
  },

  // Products
  Product: {
    filter: (params, sort, limit) => {
      const query = new URLSearchParams();
      if (params?.restaurant_id) query.set('restaurant_id', params.restaurant_id);
      if (params?.category_id) query.set('category_id', params.category_id);
      if (params?.available !== undefined) query.set('available_only', params.available);
      if (sort) query.set('sort', sort);
      if (limit) query.set('page_size', limit);
      return listAsArray(productApi.list(Object.fromEntries(query)));
    },
    create: (data) => productApi.create(data),
    update: (id, data) => productApi.update(id, data),
    delete: (id) => productApi.delete(id),
    get: (id) => productApi.get(id),
  },

  // Tables
  Table: {
    filter: (params, sort, limit) => {
      const query = new URLSearchParams();
      if (params?.restaurant_id) query.set('restaurant_id', params.restaurant_id);
      if (params?.status) query.set('status', params.status);
      if (params?.number) query.set('number', params.number);
      if (sort) query.set('sort', sort);
      if (limit) query.set('page_size', limit);
      return listAsArray(tableApi.list(Object.fromEntries(query)));
    },
    create: (data) => tableApi.create(data),
    update: (id, data) => tableApi.update(id, data),
    delete: (id) => tableApi.delete(id),
    get: (id) => tableApi.get(id),
    subscribe: (callback) => {
      // WebSocket subscription would go here
      return () => {};
    },
    bulkCreate: async (items) => {
      const results = [];
      for (const item of items) {
        results.push(await tableApi.create(item));
      }
      return results;
    },
    getQr: (id) => tableApi.getQr(id),
    getAllQr: () => tableApi.getAllQr(),
  },

  // Orders
    Order: {
      filter: (params, sort, limit) => {
        // `params.status` may be a plain string, an array, or a base44-style
        // `{ $in: [...] }` operator object. Normalize it into an array so the
        // backend receives one `status=` per value (FastAPI List[str] query).
        const query = new URLSearchParams();
        if (params?.table_id) query.set('table_id', params.table_id);
        if (params?.status) {
          let statuses = null;
          if (Array.isArray(params.status)) {
            statuses = params.status;
          } else if (typeof params.status === 'object' && params.status !== null) {
            if (Array.isArray(params.status.$in)) statuses = params.status.$in;
          } else if (typeof params.status === 'string') {
            statuses = [params.status];
          }
          if (statuses && statuses.length) {
            statuses.forEach((s) => query.append('status', String(s)));
          }
        }
        if (params?.created_date) {
          if (typeof params.created_date === 'object') {
            if (params.created_date.$gte) query.set('created_date_gte', params.created_date.$gte);
            if (params.created_date.$lte) query.set('created_date_lte', params.created_date.$lte);
          } else {
            query.set('created_date', params.created_date);
          }
        }
        if (params?.created_date_gte) query.set('created_date_gte', params.created_date_gte);
        if (params?.created_date_lte) query.set('created_date_lte', params.created_date_lte);
        if (sort) query.set('sort', sort);
        if (limit) query.set('page_size', limit);
        // Pass the query string directly (not Object.fromEntries, which would
        // collapse duplicate `status=` keys into a single value).
        return listAsArray(orderApi.list(query.toString()));
      },
      create: (data) => orderApi.create(data),
      update: (id, data) => orderApi.update(id, data),
      get: (id) => orderApi.get(id),
      subscribe: (callback) => {
        // WebSocket subscription would go here
        return () => {};
      },
      addItems: (orderId, items) => orderApi.addItems(orderId, items),
      // Public endpoints (no auth - for customer menu)
      createPublic: (restaurantId, data) => orderApi.createPublic(restaurantId, data),
      addItemsPublic: (restaurantId, orderId, items) => orderApi.addItemsPublic(restaurantId, orderId, items),
      getPublicActive: (restaurantId, tableId) => orderApi.getPublicActive(restaurantId, tableId),
    },

  // OrderItem — items come from `Order.items` (included via selectinload).
  // To keep base44-like compatibility we expose filter/create that delegate to
  // the authenticated order endpoints. `filter({ order_id })` returns the items
  // of that order, `create({ order_id, items })` appends them.
  OrderItem: {
    filter: async (params) => {
      const orderId = params?.order_id;
      if (!orderId) return [];
      const order = await orderApi.get(orderId);
      return order?.items || [];
    },
    create: async (data) => {
      const { order_id, ...itemsData } = data;
      const itemsPayload = data.items
        ? data.items
        : [{
            product_id: data.product_id,
            product_name: data.product_name,
            quantity: data.quantity,
            unit_price: data.unit_price,
            notes: data.notes,
          }];
      return orderApi.addItems(order_id, itemsPayload);
    },
    delete: (id) => orderApi.deleteItem(id),
  },

  // Employees
  Employee: {
    filter: (params, sort, limit) => {
      const query = new URLSearchParams();
      if (params?.restaurant_id) query.set('restaurant_id', params.restaurant_id);
      if (params?.active !== undefined) query.set('active_only', params.active);
      if (sort) query.set('sort', sort);
      if (limit) query.set('page_size', limit);
      return listAsArray(employeeApi.list(Object.fromEntries(query)));
    },
    create: (data) => employeeApi.create(data),
    update: (id, data) => employeeApi.update(id, data),
    delete: (id) => employeeApi.delete(id),
    get: (id) => employeeApi.get(id),
  },

  // Service Calls
    ServiceCall: {
      filter: (params, sort, limit) => {
        const query = new URLSearchParams();
        if (params?.restaurant_id) query.set('restaurant_id', params.restaurant_id);
        if (params?.status) query.set('status', params.status);
        if (sort) query.set('sort', sort);
        if (limit) query.set('page_size', limit);
        return listAsArray(serviceCallApi.list(Object.fromEntries(query)));
      },
      create: (data) => serviceCallApi.create(data),
      // Public endpoint (no auth - for customer menu)
      createPublic: (restaurantId, data) => serviceCallApi.createPublic(restaurantId, data),
      update: (id, data) => serviceCallApi.update(id, data),
      get: (id) => Promise.resolve(null),
      subscribe: (callback) => {
        return () => {};
      },
    },

  // Auth — wraps API client so callers get a single point that persists the
  // token and (when used inside the provider) syncs the user into the context.
  auth: {
    me: () => authApi.getMe(),
    login: async (email, password) => {
      const res = await authApi.login(email, password);
      if (res?.access_token) {
        localStorage.setItem('access_token', res.access_token);
      }
      return res;
    },
    register: async (email, password, fullName, restaurantName, restaurantSlug, secretKey = "123") => {
      const res = await authApi.register(email, password, fullName, restaurantName, restaurantSlug, secretKey);
      if (res?.access_token) {
        localStorage.setItem('access_token', res.access_token);
      }
      return res;
    },
    logout: () => {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    },
    redirectToLogin: (redirectUrl) => {
      window.location.href = `/login?redirect=${encodeURIComponent(redirectUrl)}`;
    },
    resetPasswordRequest: (email) => authApi.resetPasswordRequest(email),
    resetPassword: (payload) => authApi.resetPassword(payload),
  },
};

export default api;