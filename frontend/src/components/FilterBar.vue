<template>
  <div class="filter-bar">
    <!-- Search -->
    <div class="filter-bar__search">
      <span class="filter-bar__search-icon" aria-hidden="true">⌕</span>
      <input
        v-model="localTitle"
        type="search"
        class="filter-bar__input"
        :placeholder="$t('browse.search_placeholder')"
        :aria-label="$t('browse.search_placeholder')"
        @input="onTitleInput"
      />
      <button
        v-if="localTitle"
        class="filter-bar__clear"
        :aria-label="$t('browse.clear_search')"
        @click="clearTitle"
      >✕</button>
    </div>

    <!-- Rating filter -->
    <div class="filter-bar__group">
      <label class="filter-bar__label">{{ $t('common.rating') }}</label>
      <div class="filter-bar__options">
        <button
          v-for="n in ratingOptions"
          :key="n.value"
          class="filter-bar__chip"
          :class="{ 'filter-bar__chip--active': modelValue.min_rating === n.value }"
          :style="modelValue.min_rating === n.value ? { '--chip-color': domainColor } : {}"
          @click="setRating(n.value)"
        >
          {{ n.label }}
        </button>
      </div>
    </div>

    <!-- Active filter count + reset -->
    <button
      v-if="hasActiveFilters"
      class="filter-bar__reset"
      @click="$emit('reset')"
    >
      {{ $t('browse.reset_filters') }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  /** Current filter state passed from parent */
  modelValue: {
    type: Object,
    required: true,
  },
  /** Domain color for active state */
  domainColor: {
    type: String,
    default: '#c9a96e',
  },
})

const emit = defineEmits(['update:modelValue', 'reset'])

// Local debounced title state
const localTitle = ref(props.modelValue.title || '')
let debounceTimer = null

// Rating filter options
const ratingOptions = [
  { value: null, label: 'Tous' },
  { value: 1, label: '★+' },
  { value: 2, label: '★★+' },
  { value: 3, label: '★★★+' },
  { value: 4, label: '★★★★+' },
  { value: 5, label: '★★★★★' },
]

const hasActiveFilters = computed(
  () => !!props.modelValue.title || !!props.modelValue.min_rating
)

/** Debounce title input — wait 350ms after last keystroke before emitting */
function onTitleInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('update:modelValue', { ...props.modelValue, title: localTitle.value, page: 1 })
  }, 350)
}

function clearTitle() {
  localTitle.value = ''
  emit('update:modelValue', { ...props.modelValue, title: '', page: 1 })
}

function setRating(value) {
  // Toggle off if already selected
  const next = props.modelValue.min_rating === value ? null : value
  emit('update:modelValue', { ...props.modelValue, min_rating: next, page: 1 })
}

// Keep local title in sync if parent resets filters
watch(
  () => props.modelValue.title,
  (val) => { localTitle.value = val || '' }
)
</script>

<style lang="scss" scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $space-4;
  padding: $space-4 $space-5;
  background-color: $color-bg-elevated;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-lg;
  margin-bottom: $space-6;
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

  &::placeholder {
    color: $color-text-muted;
  }

  &:focus {
    outline: none;
    border-color: $color-accent;
  }

  // Remove native search clear button
  &::-webkit-search-cancel-button {
    display: none;
  }
}

.filter-bar__clear {
  position: absolute;
  right: $space-3;
  color: $color-text-muted;
  font-size: $text-xs;
  transition: color $transition-fast;

  &:hover {
    color: $color-text-primary;
  }
}

// Rating group
.filter-bar__group {
  display: flex;
  align-items: center;
  gap: $space-3;
  flex-wrap: wrap;
}

.filter-bar__label {
  font-size: $text-xs;
  color: $color-text-muted;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.filter-bar__options {
  display: flex;
  gap: $space-2;
  flex-wrap: wrap;
}

.filter-bar__chip {
  padding: $space-1 $space-3;
  border-radius: $radius-md;
  font-size: $text-xs;
  color: $color-text-secondary;
  border: 1px solid $color-border-subtle;
  background: $color-bg-card;
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

// Reset
.filter-bar__reset {
  margin-left: auto;
  font-size: $text-xs;
  color: $color-text-muted;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color $transition-fast;

  &:hover {
    color: $color-text-primary;
  }
}
</style>
