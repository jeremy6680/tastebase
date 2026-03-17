<template>
  <article
    class="item-card"
    :style="{ '--domain-color': domainColor }"
    :class="{
      'item-card--rated': item.rating,
      'item-card--selected': selected,
      'item-card--selectable': selectionMode,
    }"
    @click="onCardClick"
  >
    <!-- Selection checkbox overlay -->
    <div v-if="selectionMode || selected" class="item-card__checkbox" aria-hidden="true">
      <span class="item-card__checkbox-inner">{{ selected ? '✓' : '' }}</span>
    </div>

    <!-- Domain accent bar -->
    <div class="item-card__bar" aria-hidden="true" />

    <div class="item-card__body">
      <!-- Title + creator -->
      <div class="item-card__main">
        <h3 class="item-card__title" :title="item.title">{{ item.title }}</h3>
        <p v-if="item.creator" class="item-card__creator">{{ item.creator }}</p>
      </div>

      <!-- Category badge (if set) — hidden in selection mode -->
      <div v-if="category && !editingCategory && !selectionMode" class="item-card__category">
        <span class="item-card__category-badge" @click.stop="editingCategory = true">
          {{ categoryLabel }}
        </span>
      </div>

      <!-- Category selector (inline edit) — hidden in selection mode -->
      <div v-if="editingCategory && !selectionMode" class="item-card__category-edit">
        <CategorySelector
          v-model="categoryDraft"
          :domain="item.domain"
        />
        <div class="item-card__category-actions">
          <button
            class="item-card__category-save"
            :disabled="!categoryDraft.genre"
            @click.stop="saveCategory"
          >
            {{ $t('common.save') }}
          </button>
          <button class="item-card__category-cancel" @click.stop="cancelEdit">
            {{ $t('common.cancel') }}
          </button>
        </div>
      </div>

      <!-- Footer: year + rating + category trigger -->
      <div class="item-card__footer">
        <span v-if="item.year" class="item-card__year">{{ item.year }}</span>

        <div class="item-card__footer-right">
          <StarRating v-if="item.rating" :rating="item.rating" />
          <span v-else class="item-card__unrated">{{ $t('common.no_rating') }}</span>

          <!-- Set category button — hidden in selection mode -->
          <button
            v-if="!category && !editingCategory && !selectionMode"
            class="item-card__tag-btn"
            :title="$t('category.set')"
            @click.stop="editingCategory = true"
          >
            ⊕
          </button>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getDomain } from '@/config/domains'
import { getGenreLabel, getSubGenreLabel } from '@/config/categories'
import { fetchCategory, upsertCategory } from '@/api/categories'
import StarRating from '@/components/StarRating.vue'
import CategorySelector from '@/components/CategorySelector.vue'

const props = defineProps({
  /** TasteItemSummary object from the API */
  item: { type: Object, required: true },
  /** Whether this card is currently selected for batch operations */
  selected: { type: Boolean, default: false },
  /** Whether the grid is in selection mode (any card selected) */
  selectionMode: { type: Boolean, default: false },
  /** Externally provided category (avoids redundant API calls in batch refresh) */
  externalCategory: { type: Object, default: null },
})

const emit = defineEmits(['select'])

// Domain color
const domainColor = computed(() => getDomain(props.item.domain)?.color ?? '#c9a96e')

// Category state
const category = ref(props.externalCategory)
const editingCategory = ref(false)
const categoryDraft = ref({ genre: '', sub_genre: '' })

// When a batch apply happens, parent may push updated category down
watch(() => props.externalCategory, (val) => {
  if (val) category.value = val
})

const categoryLabel = computed(() => {
  if (!category.value) return ''
  const genre = getGenreLabel(props.item.domain, category.value.genre)
  if (!category.value.sub_genre) return genre
  const sub = getSubGenreLabel(props.item.domain, category.value.genre, category.value.sub_genre)
  return `${genre} · ${sub}`
})

/**
 * Handle card click:
 * - Cmd/Ctrl+click → emit 'select' for batch selection
 * - Normal click in selection mode → also emit 'select'
 * - Normal click otherwise → do nothing (child buttons handle their own clicks)
 */
function onCardClick(event) {
  if (event.metaKey || event.ctrlKey || props.selectionMode) {
    event.preventDefault()
    emit('select', props.item.id)
  }
}

async function loadCategory() {
  if (props.externalCategory) return
  try {
    category.value = await fetchCategory(props.item.id)
  } catch {
    category.value = null
  }
}

function cancelEdit() {
  editingCategory.value = false
  categoryDraft.value = {
    genre: category.value?.genre ?? '',
    sub_genre: category.value?.sub_genre ?? '',
  }
}

async function saveCategory() {
  if (!categoryDraft.value.genre) return
  try {
    category.value = await upsertCategory(props.item.id, {
      genre: categoryDraft.value.genre,
      sub_genre: categoryDraft.value.sub_genre || undefined,
    })
    editingCategory.value = false
  } catch (err) {
    console.error('Failed to save category:', err)
  }
}

onMounted(loadCategory)
</script>

<style lang="scss" scoped>
.item-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background-color: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-lg;
  overflow: hidden;
  transition:
    border-color $transition-fast,
    transform $transition-fast,
    box-shadow $transition-fast;

  &:hover {
    border-color: var(--domain-color);
    transform: translateY(-1px);
    box-shadow: $shadow-md;
  }

  &--rated .item-card__bar {
    background-color: var(--domain-color);
  }

  // Selectable mode: show pointer and subtle ring
  &--selectable {
    cursor: pointer;

    &:hover {
      border-color: var(--domain-color);
    }
  }

  // Selected state
  &--selected {
    border-color: var(--domain-color);
    background-color: color-mix(in srgb, var(--domain-color) 8%, $color-bg-card);
    transform: translateY(-1px);

    .item-card__bar {
      background-color: var(--domain-color);
    }
  }
}

// Checkbox overlay (top-left corner)
.item-card__checkbox {
  position: absolute;
  top: $space-2;
  left: $space-2;
  z-index: 2;
  width: 20px;
  height: 20px;
  border-radius: $radius-sm;
  border: 2px solid var(--domain-color);
  background-color: $color-bg-card;
  display: flex;
  align-items: center;
  justify-content: center;

  .item-card--selected & {
    background-color: var(--domain-color);
  }
}

.item-card__checkbox-inner {
  font-size: 11px;
  font-weight: bold;
  color: $color-bg;
  line-height: 1;
}

.item-card__bar {
  height: 2px;
  background-color: $color-border-subtle;
  flex-shrink: 0;
  transition: background-color $transition-fast;
}

.item-card__body {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  flex: 1;
  padding: $space-4;
  gap: $space-3;
}

.item-card__main { flex: 1; }

.item-card__title {
  font-family: $font-display;
  font-size: $text-base;
  font-weight: $font-weight-regular;
  color: $color-text-primary;
  line-height: $line-height-tight;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: $space-1;
}

.item-card__creator {
  font-size: $text-sm;
  color: $color-text-secondary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-card__category { display: flex; }

.item-card__category-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px $space-2;
  border-radius: $radius-sm;
  font-size: $text-xs;
  color: var(--domain-color);
  border: 1px solid currentColor;
  opacity: 0.8;
  cursor: pointer;
  transition: opacity $transition-fast;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:hover { opacity: 1; }
}

.item-card__category-edit {
  display: flex;
  flex-direction: column;
  gap: $space-2;
}

.item-card__category-actions {
  display: flex;
  gap: $space-2;
}

.item-card__category-save,
.item-card__category-cancel {
  flex: 1;
  padding: $space-1 $space-2;
  border-radius: $radius-sm;
  font-size: $text-xs;
  transition: background-color $transition-fast, color $transition-fast;
}

.item-card__category-save {
  background-color: var(--domain-color);
  color: $color-bg;
  opacity: 0.9;
  &:hover:not(:disabled) { opacity: 1; }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

.item-card__category-cancel {
  border: 1px solid $color-border-subtle;
  color: $color-text-muted;
  &:hover { color: $color-text-primary; border-color: $color-border; }
}

.item-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $space-2;
}

.item-card__footer-right {
  display: flex;
  align-items: center;
  gap: $space-2;
}

.item-card__year {
  font-size: $text-xs;
  color: $color-text-muted;
  font-variant-numeric: tabular-nums;
}

.item-card__unrated {
  font-size: $text-xs;
  color: $color-text-muted;
  font-style: italic;
}

.item-card__tag-btn {
  font-size: $text-base;
  color: $color-text-muted;
  line-height: 1;
  transition: color $transition-fast;
  &:hover { color: var(--domain-color); }
}
</style>
