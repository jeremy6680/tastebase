// src/api/categories.js — Category endpoints
import client from './client'

/**
 * Fetch the current category for an item.
 * Maps to GET /items/{itemId}/category.
 *
 * @param {string} itemId - SHA256 item identifier
 * @returns {Promise<{item_id, domain, genre, sub_genre, updated_at} | null>}
 */
export function fetchCategory(itemId) {
  return client.get(`/items/${itemId}/category`)
}

/**
 * Set or replace the genre/sub_genre for an item.
 * Maps to POST /items/{itemId}/category.
 *
 * @param {string} itemId
 * @param {{ genre: string, sub_genre?: string }} payload
 * @returns {Promise<{item_id, domain, genre, sub_genre, updated_at}>}
 */
export function upsertCategory(itemId, payload) {
  return client.post(`/items/${itemId}/category`, payload)
}
