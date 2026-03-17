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

    <!-- Selection hint — shown once any card is selected -->
    <p v-if="selectionMode" class="item-browser__selection-hint">
      {{ $t('batch.hint') }}
    </p>

    <!-- Grid -->
    <div class="item-browser__grid">

      <!-- Skeleton loading -->
      <template v-if="loading">
        <div v-for="n in filters.page_size" :key="n" class="item-card-skeleton">
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
        <button v-if="hasActiveFilters" class="item-browser__empty-reset" @click="resetFilters">
          {{ $t('browse.reset_filters') }}
        </button>
      </div>

      <!-- Item cards -->
      <ItemCard
        v-for="item in items"
        :key="item.id"
        :item="item"
        :selected="selectedIds.has(item.id)"
        :selection-mode="selectionMode"
        :external-category="appliedCategories.get(item.id) ?? null"
        @select="toggleSelection"
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

    <!-- Batch category bar (Teleported to body) -->
    <BatchCategoryBar
      :count="selectedIds.size"
      :domain="domainKey"
      :domain-color="domain.color"
      @apply="applyBatchCategory"
      @clear="clearSelection"
    />

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { fetchItems } from '@/api/items'
import { batchUpsertCategories } from '@/api/categories'
import { getDomain } from '@/config/domains'
import FilterBar from '@/components/FilterBar.vue'
import ItemCard from '@/components/ItemCard.vue'
import BatchCategoryBar from '@/components/BatchCategoryBar.vue'

const props = defineProps({
  /** Domain key: 'music' | 'book' | 'manga' | 'movie' | 'series' | 'anime' */
  domainKey: { type: String, required: true },
})

// Domain config
const domain = computed(() => getDomain(props.domainKey) || getDomain('music'))

// Filter + pagination state
const filters = ref({
  search: '',
  min_rating: null,
  decade: null,
  sort_by: 'title',
  sort_dir: 'asc',
  page: 1,
  page_size: 24,
})

// Data state
const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref(null)

// Pagination helpers
const totalPages = computed(() => Math.ceil(total.value / filters.value.page_size))
const rangeStart = computed(() => (filters.value.page - 1) * filters.value.page_size + 1)
const rangeEnd = computed(() => Math.min(filters.value.page * filters.value.page_size, total.value))
const hasActiveFilters = computed(
  () => !!filters.value.search || !!filters.value.min_rating || !!filters.value.decade
)

// ── Multi-selection state ─────────────────────────────────────────────────

/** Set of selected item IDs */
const selectedIds = ref(new Set())

/** True when at least one card is selected */
const selectionMode = computed(() => selectedIds.value.size > 0)

/**
 * Map of item_id → Category for items that were batch-categorised this session.
 * Passed down to ItemCard as externalCategory to avoid re-fetching.
 */
const appliedCategories = ref(new Map())

/** Toggle an item in/out of the selection set */
function toggleSelection(itemId) {
  const next = new Set(selectedIds.value)
  if (next.has(itemId)) {
    next.delete(itemId)
  } else {
    next.add(itemId)
  }
  selectedIds.value = next
}

/** Clear all selections */
function clearSelection() {
  selectedIds.value = new Set()
}

/**
 * Apply a category to all currently selected items via the batch endpoint.
 * Updates appliedCategories so cards reflect the change without re-fetching.
 *
 * @param {{ genre: string, sub_genre?: string }} payload
 */
async function applyBatchCategory(payload) {
  const ids = [...selectedIds.value]
  if (!ids.length) return

  try {
    const saved = await batchUpsertCategories(ids, payload)
    // Push results into the local map so cards update reactively
    const next = new Map(appliedCategories.value)
    for (const cat of saved) {
      next.set(cat.item_id, cat)
    }
    appliedCategories.value = next
    clearSelection()
  } catch (err) {
    console.error('Batch category apply failed:', err)
  }
}

// Escape key clears selection
function onKeyDown(e) {
  if (e.key === 'Escape' && selectionMode.value) {
    clearSelection()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  loadItems()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})

async function loadItems() {
  loading.value = true
  error.value = null
  try {
    const data = await fetchItems({
      domain: props.domainKey,
      search: filters.value.search || undefined,
      min_rating: filters.value.min_rating || undefined,
      decade: filters.value.decade || undefined,
      sort_by: filters.value.sort_by,
      sort_dir: filters.value.sort_dir,
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

function setPage(n) {
  filters.value = { ...filters.value, page: n }
}

function resetFilters() {
  filters.value = {
    search: '',
    min_rating: null,
    decade: null,
    sort_by: 'title',
    sort_dir: 'asc',
    page: 1,
    page_size: 24,
  }
}

watch(filters, loadItems, { deep: true })
</script>

<style lang="scss" scoped>
.item-browser {
  padding-top: $space-2;
  // Extra bottom padding so batch bar doesn't overlap last row
  padding-bottom: $space-20;
}

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

  @media (max-width: #{$bp-md - 1px}) { font-size: $text-3xl; }
}

.item-browser__count {
  font-size: $text-sm;
  color: $color-text-muted;
  margin-top: $space-2;
}

// Selection hint
.item-browser__selection-hint {
  font-size: $text-xs;
  color: $color-text-muted;
  margin-bottom: $space-4;
  font-style: italic;
}

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

.item-card-skeleton {
  background-color: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-lg;
  overflow: hidden;
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
  &:hover { color: $color-text-primary; }
}

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
  transition: color $transition-fast, border-color $transition-fast, background-color $transition-fast;

  &:hover:not(:disabled) {
    color: $color-text-primary;
    border-color: var(--domain-color);
    background-color: rgba(201, 169, 110, 0.06);
  }

  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

.pagination__info {
  font-size: $text-sm;
  color: $color-text-muted;
  font-variant-numeric: tabular-nums;
  min-width: 120px;
  text-align: center;
}

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
  &:hover { border-color: $color-accent; color: $color-accent; }
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
