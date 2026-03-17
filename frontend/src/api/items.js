// src/api/items.js — Items endpoints
import client from './client'

/**
 * Fetch a paginated, filtered, sorted list of taste items.
 * Maps to GET /items on the FastAPI backend.
 *
 * @param {Object} params - Query parameters
 * @param {string} [params.domain]      - Filter by domain key
 * @param {string} [params.status]      - Filter by status
 * @param {number} [params.min_rating]  - Minimum rating (1–5)
 * @param {string} [params.search]      - Search title OR creator (partial, case-insensitive)
 * @param {number} [params.decade]      - Filter by decade start year (e.g. 1990 for the 1990s)
 * @param {string} [params.sort_by]     - Sort field: title | creator | year | rating
 * @param {string} [params.sort_dir]    - Sort direction: asc | desc
 * @param {number} [params.page]        - Page number (1-indexed)
 * @param {number} [params.page_size]   - Items per page
 * @returns {Promise<{total: number, page: number, page_size: number, items: Array}>}
 */
export function fetchItems(params = {}) {
  // Strip undefined/null/empty string values so FastAPI doesn't receive blank params
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

/**
 * Create a new taste item.
 * Maps to POST /items/.
 *
 * @param {Object} payload
 * @param {string} payload.domain      - Domain key (music|book|manga|movie|series|anime)
 * @param {string} payload.title       - Item title (required)
 * @param {string} [payload.creator]   - Artist / author / director
 * @param {number} [payload.year]      - Release year
 * @param {number} [payload.rating]    - Initial rating (1–5)
 * @param {string} [payload.status]    - owned|watched|read|wishlist|...
 * @param {string[]} [payload.genres]  - Genre tags
 * @returns {Promise<Object>} created TasteItem
 */
/**
 * Delete a taste item permanently.
 * Maps to DELETE /items/{item_id}.
 *
 * @param {string} itemId
 * @returns {Promise<void>}
 */
export function deleteItem(itemId) {
  return client.delete(`/items/${itemId}`)
}

export function createItem(payload) {
  return client.post('/items/', {
    source: 'manual',
    source_id: null,
    external_ids: {},
    genres: [],
    ...payload,
  })
}
