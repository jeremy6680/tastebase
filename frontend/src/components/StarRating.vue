<template>
  <div
    class="star-rating"
    :class="{
      'star-rating--interactive': interactive,
      'star-rating--saving': saving,
    }"
    :role="interactive ? 'group' : 'img'"
    :aria-label="ariaLabel"
  >
    <button
      v-for="n in 5"
      :key="n"
      class="star-rating__star"
      :class="{
        'star-rating__star--filled': n <= displayRating,
        'star-rating__star--empty': n > displayRating,
        'star-rating__star--hovered': interactive && hovered >= n && hovered > 0,
      }"
      :disabled="!interactive || saving"
      :aria-label="interactive ? `${n} étoile${n > 1 ? 's' : ''}` : undefined"
      :aria-pressed="interactive ? n === currentRating : undefined"
      @mouseenter="interactive && (hovered = n)"
      @mouseleave="interactive && (hovered = 0)"
      @click.stop="interactive && onStarClick(n)"
    >★</button>

    <!-- Saving spinner -->
    <span v-if="saving" class="star-rating__spinner" aria-hidden="true">⟳</span>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  /** Current rating value (1–5). Null = unrated. */
  rating: {
    type: Number,
    default: null,
  },
  /**
   * When true, stars are clickable and emit 'update:rating'.
   * The parent is responsible for persisting the new value.
   */
  interactive: {
    type: Boolean,
    default: false,
  },
  /** Shows a spinner and disables interaction during save. */
  saving: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:rating'])

/** Hovered star index (1–5), 0 when not hovering. */
const hovered = ref(0)

/** Internal current rating (tracks optimistic updates) */
const currentRating = ref(props.rating)

// Keep in sync when parent updates the prop
import { watch } from 'vue'
watch(() => props.rating, (val) => { currentRating.value = val })

/**
 * The rating value to display — hover preview takes precedence over actual rating.
 */
const displayRating = computed(() => {
  if (props.interactive && hovered.value > 0) return hovered.value
  return currentRating.value ?? 0
})

const ariaLabel = computed(() => {
  if (!props.interactive) return `${props.rating ?? 0} étoiles sur 5`
  return currentRating.value
    ? `Note : ${currentRating.value} étoiles sur 5`
    : 'Non noté — cliquez pour noter'
})

function onStarClick(n) {
  // Optimistic update before emit so the UI responds instantly
  currentRating.value = n
  emit('update:rating', n)
}
</script>

<style lang="scss" scoped>
.star-rating {
  display: inline-flex;
  align-items: center;
  gap: 1px;
}

.star-rating__star {
  font-size: $text-sm;
  line-height: 1;
  transition: color $transition-fast, transform $transition-fast;
  background: none;
  border: none;
  padding: 0;
  cursor: default;

  &--filled {
    color: $color-accent;
  }

  &--empty {
    color: $color-text-muted;
    opacity: 0.4;
  }

  // Interactive mode
  .star-rating--interactive & {
    cursor: pointer;

    &:hover,
    &--hovered {
      transform: scale(1.2);
    }

    &:disabled {
      cursor: not-allowed;
    }
  }
}

// Saving spinner
.star-rating__spinner {
  font-size: $text-sm;
  color: $color-text-muted;
  margin-left: $space-1;
  animation: spin 1s linear infinite;
  display: inline-block;
}

.star-rating--saving .star-rating__star {
  opacity: 0.5;
  pointer-events: none;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
