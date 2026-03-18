// src/config/domains.js — Domain metadata used across the UI
// Single source of truth for icons, colors, labels, and routes per domain.

export const DOMAINS = [
    {
        key: 'music',
        route: '/music',
        color: '#e8a87c',
        // Unicode symbol used as icon (no external icon library needed)
        icon: '♪',
        labelKey: 'nav.music',
    },
    {
        key: 'book',
        route: '/books',
        color: '#7eb896',
        icon: '◈',
        labelKey: 'nav.books',
    },
    {
        key: 'manga',
        route: '/manga',
        color: '#c47bb5',
        icon: '⊞',
        labelKey: 'nav.manga',
    },
    {
        key: 'movie',
        route: '/movies',
        color: '#6ea3c8',
        icon: '◉',
        labelKey: 'nav.movies',
    },
    {
        key: 'series',
        route: '/series',
        color: '#e8c87a',
        icon: '▤',
        labelKey: 'nav.series',
    },
    {
        key: 'anime',
        route: '/anime',
        color: '#e07a7a',
        icon: '✦',
        labelKey: 'nav.anime',
    },
]

/**
 * Look up a domain config object by its key.
 *
 * @param {string} key - Domain key (e.g. 'music', 'book')
 * @returns {Object|undefined} domain config or undefined if not found
 */
export function getDomain(key) {
    return DOMAINS.find((d) => d.key === key)
}