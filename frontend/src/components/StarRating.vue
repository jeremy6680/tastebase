<template>
  <!-- Read-only star display (1–5). Non-interactive. -->
  <div class="star-rating" :aria-label="`${rating} étoiles sur 5`" role="img">
    <span
      v-for="n in 5"
      :key="n"
      class="star-rating__star"
      :class="{
        'star-rating__star--filled': n <= rating,
        'star-rating__star--empty': n > rating,
      }"
      aria-hidden="true"
    >★</span>
  </div>
</template>

<script setup>
defineProps({
  /** Current rating value (1–5). Null = unrated. */
  rating: {
    type: Number,
    default: null,
  },
})
</script>

<style lang="scss" scoped>
.star-rating {
  display: inline-flex;
  gap: 1px;
}

.star-rating__star {
  font-size: $text-sm;
  line-height: 1;
  transition: color $transition-fast;

  &--filled {
    color: $color-accent;
  }

  &--empty {
    color: $color-text-muted;
    opacity: 0.4;
  }
}
</style>
