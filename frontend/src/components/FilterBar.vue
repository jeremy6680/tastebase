<template>
  <div class="filter-bar">

    <!-- Row 1: Search + Reset -->
    <div class="filter-bar__row filter-bar__row--search">
      <div class="filter-bar__search">
        <span class="filter-bar__search-icon" aria-hidden="true">⌕</span>
        <input
          v-model="localSearch"
          type="search"
          class="filter-bar__input"
          :placeholder="$t('browse.search_placeholder')"
          :aria-label="$t('browse.search_placeholder')"
          @input="onSearchInput"
        />
        <button
          v-if="localSearch"
          class="filter-bar__clear"
          :aria-label="$t('browse.clear_search')"
          @click="clearSearch"
        >✕</button>
      </div>

      <button
        v-if="hasActiveFilters"
        class="filter-bar__reset"
        @click="$emit('reset')"
      >
        {{ $t('browse.reset_filters') }}
      </button>
    </div>

    <!-- Row 2: Filters + Sort -->
    <div class="filter-bar__row filter-bar__row--controls">

      <!-- Rating chips -->
      <div class="filter-bar__group">
        <span class="filter-bar__label">{{ $t('common.rating') }}</span>
        <div class="filter-bar__chips">
          <button
            v-for="opt in ratingOptions"
            :key="String(opt.value)"
            class="filter-bar__chip"
            :class="{ 'filter-bar__chip--active': modelValue.min_rating === opt.value }"
            :style="modelValue.min_rating === opt.value ? { '--chip-color': domainColor } : {}"
            @click="setRating(opt.value)"
          >{{ opt.label }}</button>
        </div>
      </div>

      <!-- Decade chips -->
      <div class="filter-bar__group">
        <span class="filter-bar__label">{{ $t('browse.decade') }}</span>
        <div class="filter-bar__chips">
          <button
            v-for="opt in decadeOptions"
            :key="String(opt.value)"
            class="filter-bar__chip"
            :class="{ 'filter-bar__chip--active': modelValue.decade === opt.value }"
            :style="modelValue.decade === opt.value ? { '--chip-color': domainColor } : {}"
            @click="setDecade(opt.value)"
          >{{ opt.label }}</button>
        </div>
      </div>

      <!-- Sort -->
      <div class="filter-bar__group filter-bar__group--sort">
        <span class="filter-bar__label">{{ $t('browse.sort_by') }}</span>
        <div class="filter-bar__sort">
          <select
            class="filter-bar__select"
            :value="modelValue.sort_by"
            @change="setSortBy($event.target.value)"
          >
            <option v-for="opt in sortOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <!-- Direction toggle -->
          <button
            class="filter-bar__dir-btn"
            :title="modelValue.sort_dir === 'asc' ? $t('browse.sort_desc') : $t('browse.sort_asc')"
            @click="toggleSortDir"
          >
            {{ modelValue.sort_dir === 'asc' ? '↑' : '↓' }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  /** Current filter + sort state passed from parent */
  modelValue: {
    type: Object,
    required: true,
  },
  /** Domain color for active chip state */
  domainColor: {
    type: String,
    default: '#c9a96e',
  },
})

const emit = defineEmits(['update:modelValue', 'reset'])

// ── Local debounced search ────────────────────────────────────────────────
const localSearch = ref(props.modelValue.search || '')
let debounceTimer = null

function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('update:modelValue', { ...props.modelValue, search: localSearch.value, page: 1 })
  }, 350)
}

function clearSearch() {
  localSearch.value = ''
  emit('update:modelValue', { ...props.modelValue, search: '', page: 1 })
}

watch(
  () => props.modelValue.search,
  (val) => { localSearch.value = val || '' }
)

// ── Static option lists ───────────────────────────────────────────────────

const ratingOptions = [
  { value: null,  label: t('common.all') },
  { value: 1,     label: '★+' },
  { value: 2,     label: '★★+' },
  { value: 3,     label: '★★★+' },
  { value: 4,     label: '★★★★+' },
  { value: 5,     label: '★★★★★' },
]

const decadeOptions = [
  { value: null, label: t('common.all') },
  { value: 1900, label: 'Pre-1970' },
  { value: 1970, label: '1970s' },
  { value: 1980, label: '1980s' },
  { value: 1990, label: '1990s' },
  { value: 2000, label: '2000s' },
  { value: 2010, label: '2010s' },
  { value: 2020, label: '2020s' },
]

const sortOptions = computed(() => [
  { value: 'title',   label: t('browse.sort_title') },
  { value: 'creator', label: t('browse.sort_creator') },
  { value: 'year',    label: t('browse.sort_year') },
  { value: 'rating',  label: t('browse.sort_rating') },
])

// ── Filter setters ────────────────────────────────────────────────────────

function setRating(value) {
  const next = props.modelValue.min_rating === value ? null : value
  emit('update:modelValue', { ...props.modelValue, min_rating: next, page: 1 })
}

function setDecade(value) {
  const next = props.modelValue.decade === value ? null : value
  emit('update:modelValue', { ...props.modelValue, decade: next, page: 1 })
}

function setSortBy(value) {
  emit('update:modelValue', { ...props.modelValue, sort_by: value, page: 1 })
}

function toggleSortDir() {
  const next = props.modelValue.sort_dir === 'asc' ? 'desc' : 'asc'
  emit('update:modelValue', { ...props.modelValue, sort_dir: next, page: 1 })
}

// ── Active filter indicator ───────────────────────────────────────────────

const hasActiveFilters = computed(() =>
  !!props.modelValue.search ||
  props.modelValue.min_rating !== null ||
  props.modelValue.decade !== null
)
</script>

<style lang="scss" scoped>
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: $space-3;
  padding: $space-4 $space-5;
  background-color: $color-bg-elevated;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-lg;
  margin-bottom: $space-6;
}

// Rows
.filter-bar__row {
  display: flex;
  align-items: center;
  gap: $space-4;
  flex-wrap: wrap;

  &--controls {
    gap: $space-5;
    flex-wrap: wrap;
  }
}

// Search field
.filter-bar__search {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 200px;
}

.filter-bar__search-icon {
  position: absolute;
  left: $space-3;
  color: $color-text-muted;
  font-size: $text-lg;
  pointer-events: none;
}

.filter-bar__input {
  width: 100%;
  background: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-md;
  padding: $space-2 $space-8 $space-2 $space-8;
  color: $color-text-primary;
  font-size: $text-sm;
  transition: border-color $transition-fast;

  &::placeholder { color: $color-text-muted; }

  &:focus {
    outline: none;
    border-color: $color-accent;
  }

  &::-webkit-search-cancel-button { display: none; }
}

.filter-bar__clear {
  position: absolute;
  right: $space-3;
  color: $color-text-muted;
  font-size: $text-xs;
  transition: color $transition-fast;
  &:hover { color: $color-text-primary; }
}

.filter-bar__reset {
  font-size: $text-xs;
  color: $color-text-muted;
  text-decoration: underline;
  text-underline-offset: 3px;
  white-space: nowrap;
  transition: color $transition-fast;
  &:hover { color: $color-text-primary; }
}

// Filter groups
.filter-bar__group {
  display: flex;
  align-items: center;
  gap: $space-2;
  flex-wrap: wrap;
}

.filter-bar__label {
  font-size: $text-xs;
  color: $color-text-muted;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
  flex-shrink: 0;
}

.filter-bar__chips {
  display: flex;
  gap: $space-1;
  flex-wrap: wrap;
}

.filter-bar__chip {
  padding: $space-1 $space-2;
  border-radius: $radius-md;
  font-size: $text-xs;
  color: $color-text-secondary;
  border: 1px solid $color-border-subtle;
  background: $color-bg-card;
  white-space: nowrap;
  transition:
    color $transition-fast,
    border-color $transition-fast,
    background-color $transition-fast;

  &:hover {
    color: $color-text-primary;
    border-color: $color-border;
  }

  &--active {
    color: var(--chip-color, $color-accent);
    border-color: var(--chip-color, $color-accent);
    background-color: rgba(201, 169, 110, 0.08);
  }
}

// Sort controls
.filter-bar__sort {
  display: flex;
  align-items: center;
  gap: $space-1;
}

.filter-bar__select {
  background: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-md;
  padding: $space-1 $space-3;
  color: $color-text-secondary;
  font-size: $text-xs;
  font-family: $font-body;
  cursor: pointer;
  transition: border-color $transition-fast, color $transition-fast;

  &:focus {
    outline: none;
    border-color: $color-accent;
    color: $color-text-primary;
  }

  option {
    background: $color-bg-elevated;
    color: $color-text-primary;
  }
}

.filter-bar__dir-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: $radius-md;
  border: 1px solid $color-border-subtle;
  background: $color-bg-card;
  color: $color-text-secondary;
  font-size: $text-base;
  transition:
    color $transition-fast,
    border-color $transition-fast;

  &:hover {
    color: $color-text-primary;
    border-color: $color-border;
  }
}
</style>
