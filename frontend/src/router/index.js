// src/router/index.js — Vue Router configuration
import { createRouter, createWebHistory } from 'vue-router'

// Lazy-loaded views for better initial load performance
const HomeView = () => import('@/views/HomeView.vue')
const MusicView = () => import('@/views/MusicView.vue')
const BooksView = () => import('@/views/BooksView.vue')
const MangaView = () => import('@/views/MangaView.vue')
const MoviesView = () => import('@/views/MoviesView.vue')
const SeriesView = () => import('@/views/SeriesView.vue')
const AnimeView = () => import('@/views/AnimeView.vue')

const routes = [
    {
        path: '/',
        name: 'home',
        component: HomeView,
        meta: { title: 'Accueil' },
    },
    {
        path: '/music',
        name: 'music',
        component: MusicView,
        meta: { title: 'Musique', domain: 'music' },
    },
    {
        path: '/books',
        name: 'books',
        component: BooksView,
        meta: { title: 'Livres', domain: 'book' },
    },
    {
        path: '/manga',
        name: 'manga',
        component: MangaView,
        meta: { title: 'Manga', domain: 'manga' },
    },
    {
        path: '/movies',
        name: 'movies',
        component: MoviesView,
        meta: { title: 'Films', domain: 'movie' },
    },
    {
        path: '/series',
        name: 'series',
        component: SeriesView,
        meta: { title: 'Séries', domain: 'series' },
    },
    {
        path: '/anime',
        name: 'anime',
        component: AnimeView,
        meta: { title: 'Anime', domain: 'anime' },
    },
]

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes,
    scrollBehavior(to, from, savedPosition) {
        // Restore scroll position on back navigation
        if (savedPosition) return savedPosition
        return { top: 0, behavior: 'smooth' }
    },
})

// Update document title on each navigation
router.afterEach((to) => {
    document.title = to.meta.title
        ? `${to.meta.title} — TasteBase`
        : 'TasteBase'
})

export default router