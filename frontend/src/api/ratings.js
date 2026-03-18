// src/api/ratings.js — Rating endpoints
import client from './client'

/**
 * Fetch the current rating for an item.
 * Maps to GET /items/{itemId}/ratings.
 *
 * @param {string} itemId
 * @returns {Promise<{id, item_id, rating, source, rated_at, notes} | null>}
 */
export function fetchRating(itemId) {
  return client.get(`/items/${itemId}/ratings`)
}

/**
 * Add or update the rating for an item (upsert).
 * Maps to POST /items/{itemId}/ratings.
 *
 * @param {string} itemId
 * @param {number} rating - Integer 1–5
 * @param {string} [notes]
 * @returns {Promise<{id, item_id, rating, source, rated_at, notes}>}
 */
export function upsertRating(itemId, rating, notes) {
  return client.post(`/items/${itemId}/ratings`, {
    rating,
    notes: notes ?? null,
  })
}
