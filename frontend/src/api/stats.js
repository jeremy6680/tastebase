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
 * @returns {Promise<Object>} raw profile rows grouped by stat_type
 */
export function fetchTasteProfile() {
    return client.get('/stats/taste-profile')
}

/**
 * Parse the raw taste profile response into typed buckets.
 * The API returns { profile: [{ stat_type, dimension, sub_dimension,
 * value_int, value_float, details }, ...] }.
 *
 * @param {Object} raw - Raw response from fetchTasteProfile()
 * @returns {{
 *   domainStats: Object[],
 *   topGenres: Object[],
 *   topCreators: Object[],
 *   decades: Object[]
 * }}
 */
export function parseTasteProfile(raw) {
    const rows = raw?.profile ?? []
    return {
        domainStats: rows.filter(r => r.stat_type === 'domain_stats'),
        topGenres: rows.filter(r => r.stat_type === 'top_genre'),
        topCreators: rows.filter(r => r.stat_type === 'top_creator'),
        decades: rows.filter(r => r.stat_type === 'decade'),
    }
}