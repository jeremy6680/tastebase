<template>
  <div class="category-selector">
    <!-- Genre select -->
    <select
      class="category-selector__select"
      :value="modelValue.genre"
      :aria-label="$t('category.genre')"
      @change="onGenreChange($event.target.value)"
    >
      <option value="">{{ $t('category.pick_genre') }}</option>
      <option
        v-for="genre in genres"
        :key="genre.value"
        :value="genre.value"
      >{{ genre.label }}</option>
    </select>

    <!-- Sub-genre select — only shown when selected genre has sub-genres -->
    <select
      v-if="subGenres.length > 0"
      class="category-selector__select"
      :value="modelValue.sub_genre"
      :aria-label="$t('category.sub_genre')"
      @change="onSubGenreChange($event.target.value)"
    >
      <option value="">{{ $t('category.pick_sub_genre') }}</option>
      <option
        v-for="sub in subGenres"
        :key="sub.value"
        :value="sub.value"
      >{{ sub.label }}</option>
    </select>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getGenres, getSubGenres } from '@/config/categories'

const props = defineProps({
  /** Domain key — determines which genre list to show */
  domain: {
    type: String,
    required: true,
  },
  /** Current value: { genre: string|'', sub_genre: string|'' } */
  modelValue: {
    type: Object,
    default: () => ({ genre: '', sub_genre: '' }),
  },
})

const emit = defineEmits(['update:modelValue'])

const genres = computed(() => getGenres(props.domain))

const subGenres = computed(() =>
  props.modelValue.genre ? getSubGenres(props.domain, props.modelValue.genre) : []
)

function onGenreChange(genre) {
  // Reset sub_genre when genre changes
  emit('update:modelValue', { genre, sub_genre: '' })
}

function onSubGenreChange(sub_genre) {
  emit('update:modelValue', { ...props.modelValue, sub_genre })
}
</script>

<style lang="scss" scoped>
.category-selector {
  display: flex;
  flex-direction: column;
  gap: $space-2;
}

.category-selector__select {
  width: 100%;
  background: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-md;
  padding: $space-2 $space-3;
  color: $color-text-primary;
  font-size: $text-sm;
  font-family: $font-body;
  cursor: pointer;
  transition: border-color $transition-fast;

  &:focus {
    outline: none;
    border-color: $color-accent;
  }

  option {
    background: $color-bg-elevated;
    color: $color-text-primary;
  }
}
</style>
