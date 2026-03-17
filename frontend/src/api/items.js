// src/api/items.js — Items endpoints
import client from './client'

/**
 * Fetch a paginated, filtered list of taste items.
 * Maps to GET /items on the FastAPI backend.
 *
 * @param {Object} params - Query parameters
 * @param {string} [params.domain]      - Filter by domain key
 * @param {string} [params.status]      - Filter by status
 * @param {number} [params.min_rating]  - Minimum rating (1–5)
 * @param {string} [params.title]       - Partial title search
 * @param {number} [params.page]        - Page number (1-indexed)
 * @param {number} [params.page_size]   - Items per page
 * @returns {Promise<{total: number, page: number, page_size: number, items: Array}>}
 */
export function fetchItems(params = {}) {
  // Strip undefined/null/empty values so FastAPI doesn't receive blank params
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  )
  return client.get('/items/', { params: clean })
}

/**
 * Fetch a single taste item by ID.
 * Maps to GET /items/{item_id}.
 *
 * @param {string} itemId - SHA256 item identifier
 * @returns {Promise<Object>} full item with current rating
 */
export function fetchItem(itemId) {
  return client.get(`/items/${itemId}`)
}
