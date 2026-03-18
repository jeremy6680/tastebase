// src/config/categories.js
// Genre / sub-genre taxonomy per domain.
// Single source of truth used by CategorySelector and API validation.

/**
 * @typedef {Object} SubGenre
 * @property {string} value
 * @property {string} label
 */

/**
 * @typedef {Object} Genre
 * @property {string} value
 * @property {string} label
 * @property {SubGenre[]} subGenres
 */

/** @type {Record<string, Genre[]>} */
export const CATEGORIES = {
  book: [
    {
      value: 'fiction',
      label: 'Romans',
      subGenres: [
        { value: 'classics',       label: 'Classiques' },
        { value: 'contemporary',   label: 'Contemporains' },
        { value: 'sci-fi',         label: 'Science-fiction' },
        { value: 'fantasy',        label: 'Fantasy' },
        { value: 'thriller',       label: 'Policier' },
        { value: 'humor',          label: 'Humour' },
      ],
    },
    {
      value: 'non-fiction',
      label: 'Non-fiction',
      subGenres: [
        { value: 'biography',      label: 'Biographies' },
        { value: 'history',        label: 'Histoire' },
        { value: 'essay',          label: 'Essais' },
        { value: 'science',        label: 'Sciences' },
        { value: 'philosophy',     label: 'Philosophie' },
        { value: 'psychology',     label: 'Psychologie' },
        { value: 'self-help',      label: 'Développement personnel' },
        { value: 'politics',       label: 'Politique / société' },
        { value: 'economics',      label: 'Économie' },
        { value: 'religion',       label: 'Religion / spiritualité' },
        { value: 'travel',         label: 'Voyage' },
      ],
    },
    {
      value: 'practical',
      label: 'Pratique / Loisirs',
      subGenres: [
        { value: 'cooking',        label: 'Cuisine' },
        { value: 'art',            label: 'Art / photographie' },
        { value: 'sport',          label: 'Sport' },
        { value: 'diy',            label: 'Bricolage' },
        { value: 'tech',           label: 'Informatique / technologie' },
        { value: 'languages',      label: 'Langues' },
        { value: 'gardening',      label: 'Jardinage' },
      ],
    },
    {
      value: 'other',
      label: 'Autres',
      subGenres: [
        { value: 'poetry',         label: 'Poésie' },
        { value: 'theater',        label: 'Théâtre' },
        { value: 'coffee-table',   label: 'Beaux livres' },
        { value: 'misc',           label: 'Autres' },
      ],
    },
  ],

  music: [
    {
      value: 'rock-indie',
      label: '🎸 Rock / Indie',
      subGenres: [
        { value: 'indie-rock',     label: 'Indie rock' },
        { value: 'pop-rock',       label: 'Pop rock' },
        { value: 'noise-rock',     label: 'Noise rock' },
        { value: 'post-rock',      label: 'Post-rock' },
        { value: 'shoegaze',       label: 'Shoegaze' },
        { value: 'dream-pop',      label: 'Dream pop' },
      ],
    },
    {
      value: 'punk-hardcore',
      label: '⚡ Punk / Hardcore',
      subGenres: [
        { value: 'punk-rock',      label: 'Punk rock' },
        { value: 'hardcore',       label: 'Punk hardcore' },
        { value: 'post-hardcore',  label: 'Post-hardcore' },
        { value: 'emo',            label: 'Emo' },
        { value: 'screamo',        label: 'Screamo' },
      ],
    },
    {
      value: 'metal',
      label: '🤘 Metal',
      subGenres: [
        { value: 'heavy-metal',    label: 'Heavy metal' },
        { value: 'black-metal',    label: 'Black metal' },
        { value: 'post-metal',     label: 'Post-metal' },
        { value: 'blackgaze',      label: 'Blackgaze' },
        { value: 'sludge-doom',    label: 'Sludge / doom' },
      ],
    },
    {
      value: 'french-rock',
      label: '🇫🇷 Rock français',
      subGenres: [
        { value: 'fr-alt-rock',    label: 'Rock alternatif français' },
        { value: 'fr-indie',       label: 'Indie français' },
        { value: 'chanson-rock',   label: 'Chanson rock' },
      ],
    },
    {
      value: 'electronic',
      label: '🎧 Électronique',
      subGenres: [
        { value: 'dnb',            label: 'Drum and bass' },
        { value: 'jungle',         label: 'Jungle' },
        { value: 'ambient',        label: 'Ambient' },
        { value: 'trip-hop',       label: 'Trip hop' },
      ],
    },
    {
      value: 'jazz',
      label: '🎷 Jazz',
      subGenres: [
        { value: 'classic-jazz',   label: 'Jazz classique' },
        { value: 'experimental-jazz', label: 'Jazz expérimental' },
        { value: 'jazz-fusion',    label: 'Jazz fusion' },
      ],
    },
    {
      value: 'classical',
      label: '🎻 Classique',
      subGenres: [
        { value: 'baroque',        label: 'Baroque' },
        { value: 'romantic',       label: 'Romantique' },
        { value: 'modern-classical', label: 'Moderne / contemporain' },
      ],
    },
    {
      value: 'hip-hop',
      label: '🎤 Hip-hop / Rap',
      subGenres: [
        { value: 'classic-hiphop', label: 'Hip-hop classique' },
        { value: 'alt-hiphop',     label: 'Hip-hop alternatif' },
        { value: 'instrumental-hiphop', label: 'Instrumental / expérimental' },
      ],
    },
    {
      value: 'world',
      label: '🌍 World / musiques du monde',
      subGenres: [
        { value: 'afrobeat',       label: 'Afrobeat' },
        { value: 'african',        label: 'Musiques africaines' },
        { value: 'latin-american', label: 'Musiques latino-américaines' },
        { value: 'folk',           label: 'Folk traditionnel' },
        { value: 'world-other',    label: 'Autres' },
      ],
    },
  ],

  movie: [
    {
      value: 'drama-comedy',
      label: 'Comédie dramatique',
      subGenres: [],
    },
    {
      value: 'comedy',
      label: 'Humour',
      subGenres: [],
    },
    {
      value: 'documentary',
      label: 'Documentaires',
      subGenres: [],
    },
    {
      value: 'sport',
      label: 'Sports',
      subGenres: [],
    },
    {
      value: 'music',
      label: 'Musique',
      subGenres: [],
    },
    {
      value: 'other',
      label: 'Autres',
      subGenres: [],
    },
  ],

  series: [
    {
      value: 'comedy',
      label: 'Comédies',
      subGenres: [],
    },
    {
      value: 'drama',
      label: 'Dramas',
      subGenres: [],
    },
    {
      value: 'documentary',
      label: 'Documentaires',
      subGenres: [],
    },
    {
      value: 'music',
      label: 'Musique',
      subGenres: [],
    },
    {
      value: 'other',
      label: 'Autres',
      subGenres: [],
    },
  ],

  anime: [
    { value: 'shonen',  label: 'Shōnen',  subGenres: [] },
    { value: 'shojo',   label: 'Shōjo',   subGenres: [] },
    { value: 'seinen',  label: 'Seinen',  subGenres: [] },
    { value: 'josei',   label: 'Josei',   subGenres: [] },
    { value: 'other',   label: 'Autres',  subGenres: [] },
  ],

  manga: [
    { value: 'shonen',  label: 'Shōnen',  subGenres: [] },
    { value: 'shojo',   label: 'Shōjo',   subGenres: [] },
    { value: 'seinen',  label: 'Seinen',  subGenres: [] },
    { value: 'josei',   label: 'Josei',   subGenres: [] },
    { value: 'other',   label: 'Autres',  subGenres: [] },
  ],
}

/**
 * Get genre list for a given domain.
 *
 * @param {string} domain - Domain key
 * @returns {Genre[]} genres for that domain, or []
 */
export function getGenres(domain) {
  return CATEGORIES[domain] ?? []
}

/**
 * Get sub-genres for a given domain + genre.
 *
 * @param {string} domain
 * @param {string} genreValue
 * @returns {SubGenre[]}
 */
export function getSubGenres(domain, genreValue) {
  const genre = getGenres(domain).find((g) => g.value === genreValue)
  return genre?.subGenres ?? []
}

/**
 * Resolve a genre label from its value.
 *
 * @param {string} domain
 * @param {string} genreValue
 * @returns {string}
 */
export function getGenreLabel(domain, genreValue) {
  return getGenres(domain).find((g) => g.value === genreValue)?.label ?? genreValue
}

/**
 * Resolve a sub-genre label from its value.
 *
 * @param {string} domain
 * @param {string} genreValue
 * @param {string} subGenreValue
 * @returns {string}
 */
export function getSubGenreLabel(domain, genreValue, subGenreValue) {
  return getSubGenres(domain, genreValue).find((s) => s.value === subGenreValue)?.label ?? subGenreValue
}
