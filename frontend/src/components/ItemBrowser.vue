<template>
  <div class="item-browser" :style="{ '--domain-color': domain.color }">

    <!-- Page header -->
    <header class="item-browser__header">
      <div class="item-browser__icon">{{ domain.icon }}</div>
      <div>
        <h1 class="item-browser__title">{{ $t(domain.labelKey) }}</h1>
        <p class="item-browser__count">
          <template v-if="!loading && total > 0">
            {{ total }} {{ $t('common.items', total) }}
          </template>
          <template v-else-if="loading">
            {{ $t('common.loading') }}
          </template>
        </p>
      </div>
    </header>

    <!-- Filters -->
    <FilterBar
      v-model="filters"
      :domain-color="domain.color"
      @reset="resetFilters"
    />

    <!-- Grid -->
    <div class="item-browser__grid">

      <!-- Skeleton loading -->
      <template v-if="loading">
        <div
          v-for="n in filters.page_size"
          :key="n"
          class="item-card-skeleton"
        >
          <div class="item-card-skeleton__bar" />
          <div class="item-card-skeleton__body">
            <div class="skeleton skeleton--title" />
            <div class="skeleton skeleton--creator" />
            <div class="skeleton skeleton--footer" />
          </div>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else-if="!loading && items.length === 0" class="item-browser__empty">
        <p class="item-browser__empty-icon">◎</p>
        <p class="item-browser__empty-text">{{ $t('browse.no_results') }}</p>
        <button
          v-if="hasActiveFilters"
          class="item-browser__empty-reset"
          @click="resetFilters"
        >
          {{ $t('browse.reset_filters') }}
        </button>
      </div>

      <!-- Item cards -->
      <ItemCard
        v-for="item in items"
        :key="item.id"
        :item="item"
      />
    </div>

    <!-- Pagination -->
    <div v-if="!loading && totalPages > 1" class="item-browser__pagination">
      <button
        class="pagination__btn"
        :disabled="filters.page <= 1"
        :aria-label="$t('browse.previous_page')"
        @click="setPage(filters.page - 1)"
      >‹</button>

      <span class="pagination__info">
        {{ rangeStart }}–{{ rangeEnd }} / {{ total }}
      </span>

      <button
        class="pagination__btn"
        :disabled="filters.page >= totalPages"
        :aria-label="$t('browse.next_page')"
        @click="setPage(filters.page + 1)"
      >›</button>
    </div>

    <!-- Error state -->
    <div v-if="error" class="item-browser__error">
      <p>{{ $t('common.error') }}</p>
      <button class="item-browser__retry" @click="loadItems">{{ $t('common.retry') }}</button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { fetchItems } from '@/api/items'
import { getDomain } from '@/config/domains'
import FilterBar from '@/components/FilterBar.vue'
import ItemCard from '@/components/ItemCard.vue'

const props = defineProps({
  /** Domain key: 'music' | 'book' | 'manga' | 'movie' | 'series' | 'anime' */
  domainKey: {
    type: String,
    required: true,
  },
})

// Domain config (color, icon, label)
const domain = computed(() => getDomain(props.domainKey) || getDomain('music'))

// Filter + pagination state
const filters = ref({
  title: '',
  min_rating: null,
  page: 1,
  page_size: 24,
})

// Data state
const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref(null)

// Computed pagination helpers
const totalPages = computed(() => Math.ceil(total.value / filters.value.page_size))
const rangeStart = computed(() => (filters.value.page - 1) * filters.value.page_size + 1)
const rangeEnd = computed(() => Math.min(filters.value.page * filters.value.page_size, total.value))
const hasActiveFilters = computed(() => !!filters.value.title || !!filters.value.min_rating)

/**
 * Fetch items from the API using current filter state.
 */
async function loadItems() {
  loading.value = true
  error.value = null

  try {
    const data = await fetchItems({
      domain: props.domainKey,
      title: filters.value.title || undefined,
      min_rating: filters.value.min_rating || undefined,
      page: filters.value.page,
      page_size: filters.value.page_size,
    })
    items.value = data.items
    total.value = data.total
  } catch (err) {
    error.value = err.message
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/** Navigate to a specific page */
function setPage(n) {
  filters.value = { ...filters.value, page: n }
}

/** Reset all filters to defaults */
function resetFilters() {
  filters.value = { title: '', min_rating: null, page: 1, page_size: 24 }
}

// Re-fetch whenever filters change
watch(filters, loadItems, { deep: true })

onMounted(loadItems)
</script>

<style lang="scss" scoped>
.item-browser {
  padding-top: $space-2;
}

// Header
.item-browser__header {
  display: flex;
  align-items: center;
  gap: $space-6;
  margin-bottom: $space-8;
}

.item-browser__icon {
  font-size: 3rem;
  color: var(--domain-color);
  line-height: 1;
  flex-shrink: 0;
}

.item-browser__title {
  font-family: $font-display;
  font-size: $text-5xl;
  font-weight: $font-weight-light;
  color: $color-text-primary;
  letter-spacing: -0.03em;
  line-height: $line-height-tight;

  @media (max-width: #{$bp-md - 1px}) {
    font-size: $text-3xl;
  }
}

.item-browser__count {
  font-size: $text-sm;
  color: $color-text-muted;
  margin-top: $space-2;
}

// Grid
.item-browser__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: $space-4;
  min-height: 200px;

  @media (max-width: #{$bp-sm - 1px}) {
    grid-template-columns: repeat(2, 1fr);
    gap: $space-3;
  }
}

// Skeleton card
.item-card-skeleton {
  background-color: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-lg;
  overflow: hidden;
  animation: card-enter 0.4s ease both;
}

.item-card-skeleton__bar {
  height: 2px;
  @extend .skeleton;
}

.item-card-skeleton__body {
  padding: $space-4;
  display: flex;
  flex-direction: column;
  gap: $space-3;
}

// Skeleton placeholders
.skeleton {
  background: linear-gradient(
    90deg,
    $color-bg-elevated 25%,
    rgba(255,255,255,0.04) 50%,
    $color-bg-elevated 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: $radius-sm;

  &--title   { height: 16px; width: 80%; }
  &--creator { height: 12px; width: 55%; }
  &--footer  { height: 12px; width: 40%; margin-top: $space-2; }
}

// Empty state
.item-browser__empty {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $space-16;
  gap: $space-4;
  text-align: center;
}

.item-browser__empty-icon {
  font-size: 2rem;
  color: $color-text-muted;
  opacity: 0.5;
}

.item-browser__empty-text {
  font-size: $text-base;
  color: $color-text-secondary;
}

.item-browser__empty-reset {
  font-size: $text-sm;
  color: $color-text-muted;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color $transition-fast;

  &:hover {
    color: $color-text-primary;
  }
}

// Pagination
.item-browser__pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $space-6;
  padding-top: $space-8;
  border-top: 1px solid $color-border-subtle;
  margin-top: $space-8;
}

.pagination__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: $radius-md;
  border: 1px solid $color-border-subtle;
  color: $color-text-secondary;
  font-size: $text-xl;
  transition:
    color $transition-fast,
    border-color $transition-fast,
    background-color $transition-fast;

  &:hover:not(:disabled) {
    color: $color-text-primary;
    border-color: var(--domain-color);
    background-color: rgba(201, 169, 110, 0.06);
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
}

.pagination__info {
  font-size: $text-sm;
  color: $color-text-muted;
  font-variant-numeric: tabular-nums;
  min-width: 120px;
  text-align: center;
}

// Error
.item-browser__error {
  text-align: center;
  padding: $space-8;
  color: $color-text-secondary;
}

.item-browser__retry {
  margin-top: $space-3;
  padding: $space-2 $space-5;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  font-size: $text-sm;
  color: $color-text-secondary;
  transition: border-color $transition-fast, color $transition-fast;

  &:hover {
    border-color: $color-accent;
    color: $color-accent;
  }
}

@keyframes card-enter {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes skeleton-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
