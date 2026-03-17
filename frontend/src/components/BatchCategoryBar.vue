<template>
  <Teleport to="body">
    <Transition name="batch-bar">
      <div v-if="count > 0" class="batch-bar" :style="{ '--domain-color': domainColor }">
        <div class="batch-bar__inner">

          <!-- Selection info -->
          <div class="batch-bar__info">
            <span class="batch-bar__count">{{ count }}</span>
            <span class="batch-bar__label">{{ $t('batch.selected', count) }}</span>
            <button class="batch-bar__clear" @click="$emit('clear')">
              {{ $t('batch.clear') }}
            </button>
          </div>

          <!-- Category selector -->
          <div class="batch-bar__selector">
            <CategorySelector
              v-model="categoryDraft"
              :domain="domain"
            />
          </div>

          <!-- Apply button -->
          <button
            class="batch-bar__apply"
            :disabled="!categoryDraft.genre || applying"
            @click="apply"
          >
            <span v-if="applying">{{ $t('common.loading') }}</span>
            <span v-else>{{ $t('batch.apply') }}</span>
          </button>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import CategorySelector from '@/components/CategorySelector.vue'

const props = defineProps({
  /** Number of selected items */
  count: { type: Number, required: true },
  /** Domain key for the CategorySelector */
  domain: { type: String, required: true },
  /** Domain color for accent */
  domainColor: { type: String, default: '#c9a96e' },
})

const emit = defineEmits(['apply', 'clear'])

const categoryDraft = ref({ genre: '', sub_genre: '' })
const applying = ref(false)

async function apply() {
  if (!categoryDraft.value.genre || applying.value) return
  applying.value = true
  try {
    await emit('apply', {
      genre: categoryDraft.value.genre,
      sub_genre: categoryDraft.value.sub_genre || undefined,
    })
    // Reset draft after successful apply
    categoryDraft.value = { genre: '', sub_genre: '' }
  } finally {
    applying.value = false
  }
}
</script>

<style lang="scss" scoped>
.batch-bar {
  position: fixed;
  bottom: $space-6;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  width: min(760px, calc(100vw - #{$space-8}));
}

.batch-bar__inner {
  display: flex;
  align-items: center;
  gap: $space-4;
  padding: $space-4 $space-6;
  background-color: $color-bg-elevated;
  border: 1px solid var(--domain-color);
  border-radius: $radius-xl;
  box-shadow: $shadow-lg, 0 0 0 1px rgba(var(--domain-color), 0.1);

  @media (max-width: #{$bp-md - 1px}) {
    flex-direction: column;
    align-items: stretch;
  }
}

// Info section
.batch-bar__info {
  display: flex;
  align-items: center;
  gap: $space-2;
  flex-shrink: 0;
}

.batch-bar__count {
  font-family: $font-display;
  font-size: $text-2xl;
  font-weight: $font-weight-light;
  color: var(--domain-color);
  line-height: 1;
}

.batch-bar__label {
  font-size: $text-sm;
  color: $color-text-secondary;
  white-space: nowrap;
}

.batch-bar__clear {
  font-size: $text-xs;
  color: $color-text-muted;
  text-decoration: underline;
  text-underline-offset: 3px;
  white-space: nowrap;
  transition: color $transition-fast;
  margin-left: $space-2;

  &:hover { color: $color-text-primary; }
}

// Selector
.batch-bar__selector {
  flex: 1;
  min-width: 0;

  // Override CategorySelector to be horizontal on desktop
  :deep(.category-selector) {
    flex-direction: row;
    gap: $space-2;

    @media (max-width: #{$bp-md - 1px}) {
      flex-direction: column;
    }
  }
}

// Apply button
.batch-bar__apply {
  flex-shrink: 0;
  padding: $space-2 $space-6;
  border-radius: $radius-md;
  background-color: var(--domain-color);
  color: $color-bg;
  font-size: $text-sm;
  font-weight: $font-weight-medium;
  opacity: 0.9;
  transition: opacity $transition-fast;

  &:hover:not(:disabled) { opacity: 1; }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

// Slide-up transition
.batch-bar-enter-active,
.batch-bar-leave-active {
  transition: transform $transition-normal, opacity $transition-normal;
}

.batch-bar-enter-from,
.batch-bar-leave-to {
  transform: translateX(-50%) translateY(20px);
  opacity: 0;
}
</style>
