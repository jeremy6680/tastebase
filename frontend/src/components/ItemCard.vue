<template>
  <article
    class="item-card"
    :style="{ '--domain-color': domainColor }"
    :class="{ 'item-card--rated': item.rating }"
  >
    <!-- Domain accent bar -->
    <div class="item-card__bar" aria-hidden="true" />

    <div class="item-card__body">
      <!-- Title + creator -->
      <div class="item-card__main">
        <h3 class="item-card__title" :title="item.title">{{ item.title }}</h3>
        <p v-if="item.creator" class="item-card__creator">{{ item.creator }}</p>
      </div>

      <!-- Footer: year + rating -->
      <div class="item-card__footer">
        <span v-if="item.year" class="item-card__year">{{ item.year }}</span>
        <StarRating v-if="item.rating" :rating="item.rating" />
        <span v-else class="item-card__unrated">{{ $t('common.no_rating') }}</span>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { getDomain } from '@/config/domains'
import StarRating from '@/components/StarRating.vue'

const props = defineProps({
  /** TasteItemSummary object from the API */
  item: {
    type: Object,
    required: true,
  },
})

const domainColor = computed(() => {
  const d = getDomain(props.item.domain)
  return d?.color ?? '#c9a96e'
})
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
}

// Thin color bar at top
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

.item-card__main {
  flex: 1;
}

.item-card__title {
  font-family: $font-display;
  font-size: $text-base;
  font-weight: $font-weight-regular;
  color: $color-text-primary;
  line-height: $line-height-tight;
  // Clamp to 2 lines
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

.item-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
</style>
