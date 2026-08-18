// NEV2 API Client - replaces @base44/sdk
// This provides the same interface as base44Client.js but uses our own backend

import { api } from '@/lib/restaurant-context';

// Export the same interface that was used before
export const base44 = {
  entities: api,
  auth: api.auth,
};

// Also export individual services for direct use
export const { 
  restaurant, 
  Category, 
  Product, 
  Table, 
  Order, 
  OrderItem, 
  Employee, 
  ServiceCall,
  auth 
} = api;

export default base44;