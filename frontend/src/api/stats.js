// src/api/stats.js — Stats endpoints (domain counts, taste profile)
import client from './client'

/**
 * Fetch item counts per domain.
 * Maps to GET /stats/counts on the FastAPI backend.
 *
 * @returns {Promise<Object>} counts keyed by domain name
 */
export function fetchCounts() {
    return client.get('/stats/counts')
}

/**
 * Fetch recently added items across all domains.
 * Maps to GET /stats/recent on the FastAPI backend.
 *
 * @param {number} limit - Number of items to return (default 10)
 * @returns {Promise<Array>} list of recently added taste items
 */
export function fetchRecent(limit = 10) {
    return client.get('/stats/recent', { params: { limit } })
}

/**
 * Fetch the taste profile (top genres, creators, decades).
 * Maps to GET /stats/taste-profile on the FastAPI backend.
 *
 * @returns {Promise<Object>} taste profile aggregate data
 */
export function fetchTasteProfile() {
    return client.get('/stats/taste-profile')
}