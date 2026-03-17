<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="modelValue"
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('add_item.title')"
        @mousedown.self="close"
      >
        <div class="modal" :style="{ '--domain-color': domainColor }">

          <!-- Header -->
          <div class="modal__header">
            <span class="modal__domain-icon">{{ domainIcon }}</span>
            <h2 class="modal__title">{{ $t('add_item.title') }}</h2>
            <button class="modal__close" :aria-label="$t('common.cancel')" @click="close">✕</button>
          </div>

          <div class="modal__body">
            <!-- Title (required) -->
            <div class="modal__field">
              <label class="modal__label" for="add-title">
                {{ $t('add_item.field_title') }}
                <span class="modal__required" aria-hidden="true">*</span>
              </label>
              <input
                id="add-title"
                v-model="form.title"
                type="text"
                class="modal__input"
                :class="{ 'modal__input--error': errors.title }"
                :placeholder="$t('add_item.placeholder_title')"
                autocomplete="off"
                @blur="validateTitle"
              />
              <p v-if="errors.title" class="modal__error">{{ errors.title }}</p>
            </div>

            <!-- Creator -->
            <div class="modal__field">
              <label class="modal__label" for="add-creator">{{ $t('add_item.field_creator') }}</label>
              <input
                id="add-creator"
                v-model="form.creator"
                type="text"
                class="modal__input"
                :placeholder="creatorPlaceholder"
                autocomplete="off"
              />
            </div>

            <!-- Year + Rating row -->
            <div class="modal__row">
              <div class="modal__field modal__field--half">
                <label class="modal__label" for="add-year">{{ $t('add_item.field_year') }}</label>
                <input
                  id="add-year"
                  v-model.number="form.year"
                  type="number"
                  class="modal__input"
                  :class="{ 'modal__input--error': errors.year }"
                  min="1800"
                  max="2100"
                  :placeholder="new Date().getFullYear().toString()"
                  @blur="validateYear"
                />
                <p v-if="errors.year" class="modal__error">{{ errors.year }}</p>
              </div>

              <div class="modal__field modal__field--half">
                <label class="modal__label">{{ $t('add_item.field_rating') }}</label>
                <div class="modal__rating">
                  <button
                    v-for="n in 5"
                    :key="n"
                    type="button"
                    class="modal__star"
                    :class="{
                      'modal__star--filled': n <= (hoverRating || form.rating || 0),
                      'modal__star--hovered': n <= hoverRating,
                    }"
                    :aria-label="`${n} étoile${n > 1 ? 's' : ''}`"
                    @mouseenter="hoverRating = n"
                    @mouseleave="hoverRating = 0"
                    @click="toggleRating(n)"
                  >★</button>
                  <button
                    v-if="form.rating"
                    type="button"
                    class="modal__rating-clear"
                    :aria-label="$t('add_item.clear_rating')"
                    @click="form.rating = null"
                  >✕</button>
                </div>
              </div>
            </div>

            <!-- Status -->
            <div class="modal__field">
              <label class="modal__label" for="add-status">{{ $t('add_item.field_status') }}</label>
              <select id="add-status" v-model="form.status" class="modal__select">
                <option value="">{{ $t('add_item.status_none') }}</option>
                <option v-for="s in statusOptions" :key="s.value" :value="s.value">
                  {{ s.label }}
                </option>
              </select>
            </div>

            <!-- Genre / sous-genre (facultatif) -->
            <div class="modal__field">
              <label class="modal__label">
                {{ $t('category.genre') }}
                <span class="modal__optional">({{ $t('common.optional') }})</span>
              </label>
              <CategorySelector
                v-model="form.category"
                :domain="domainKey"
              />
            </div>
          </div>

          <!-- Footer -->
          <div class="modal__footer">
            <button class="modal__btn modal__btn--cancel" @click="close">
              {{ $t('common.cancel') }}
            </button>
            <button
              class="modal__btn modal__btn--submit"
              :disabled="submitting || !form.title.trim()"
              @click="submit"
            >
              <span v-if="submitting">{{ $t('common.loading') }}</span>
              <span v-else>{{ $t('add_item.submit') }}</span>
            </button>
          </div>

          <!-- Submit error -->
          <p v-if="submitError" class="modal__submit-error">{{ submitError }}</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDomain } from '@/config/domains'
import { createItem } from '@/api/items'
import { upsertCategory } from '@/api/categories'
import CategorySelector from '@/components/CategorySelector.vue'

const { t } = useI18n()

const props = defineProps({
  /** Controls modal visibility (v-model) */
  modelValue: { type: Boolean, default: false },
  /** Domain key — pre-fills domain, icon, color */
  domainKey: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue', 'created'])

// Domain metadata
const domainConfig = computed(() => getDomain(props.domainKey))
const domainColor = computed(() => domainConfig.value?.color ?? '#c9a96e')
const domainIcon = computed(() => domainConfig.value?.icon ?? '◈')

// Status options vary slightly by domain
const statusOptions = computed(() => {
  const domain = props.domainKey
  if (domain === 'music') {
    return [
      { value: 'owned',            label: t('add_item.status_owned') },
      { value: 'previously_owned', label: t('add_item.status_prev_owned') },
      { value: 'wishlist',         label: t('add_item.status_wishlist') },
    ]
  }
  if (domain === 'book' || domain === 'manga') {
    return [
      { value: 'read',     label: t('add_item.status_read') },
      { value: 'owned',    label: t('add_item.status_owned') },
      { value: 'unread',   label: t('add_item.status_unread') },
      { value: 'wishlist', label: t('add_item.status_wishlist') },
    ]
  }
  // movie, series, anime
  return [
    { value: 'watched',  label: t('add_item.status_watched') },
    { value: 'wishlist', label: t('add_item.status_wishlist') },
  ]
})

// Creator field placeholder per domain
const creatorPlaceholder = computed(() => {
  const map = {
    music: t('add_item.placeholder_artist'),
    book: t('add_item.placeholder_author'),
    manga: t('add_item.placeholder_author'),
    movie: t('add_item.placeholder_director'),
    series: t('add_item.placeholder_creator'),
    anime: t('add_item.placeholder_studio'),
  }
  return map[props.domainKey] ?? t('add_item.placeholder_creator')
})

// Form state
const emptyForm = () => ({
  title: '',
  creator: '',
  year: null,
  rating: null,
  status: '',
  category: { genre: '', sub_genre: '' },
})

const form = ref(emptyForm())
const errors = ref({ title: '', year: '' })
const hoverRating = ref(0)
const submitting = ref(false)
const submitError = ref('')

// Reset form when modal opens
watch(() => props.modelValue, (open) => {
  if (open) {
    form.value = emptyForm()
    errors.value = { title: '', year: '' }
    submitError.value = ''
    hoverRating.value = 0
  }
})

// Escape key closes modal
function onKeyDown(e) {
  if (e.key === 'Escape') close()
}

watch(() => props.modelValue, (open) => {
  if (open) {
    window.addEventListener('keydown', onKeyDown)
  } else {
    window.removeEventListener('keydown', onKeyDown)
  }
})

function close() {
  emit('update:modelValue', false)
}

// Validation
function validateTitle() {
  errors.value.title = form.value.title.trim()
    ? ''
    : t('add_item.error_title_required')
}

function validateYear() {
  const y = form.value.year
  if (y === null || y === '') {
    errors.value.year = ''
    return
  }
  if (y < 1800 || y > 2100) {
    errors.value.year = t('add_item.error_year_range')
  } else {
    errors.value.year = ''
  }
}

/** Toggle rating: clicking the same star again deselects it */
function toggleRating(n) {
  form.value.rating = form.value.rating === n ? null : n
}

async function submit() {
  validateTitle()
  validateYear()
  if (errors.value.title || errors.value.year) return
  if (!form.value.title.trim()) return

  submitting.value = true
  submitError.value = ''

  try {
    const payload = {
      domain: props.domainKey,
      title: form.value.title.trim(),
      creator: form.value.creator.trim() || undefined,
      year: form.value.year || undefined,
      rating: form.value.rating || undefined,
      status: form.value.status || undefined,
    }
    const created = await createItem(payload)

    // Save category if a genre was selected
    if (form.value.category.genre) {
      try {
        await upsertCategory(created.id, {
          genre: form.value.category.genre,
          sub_genre: form.value.category.sub_genre || undefined,
        })
      } catch {
        // Category save failure is non-fatal — item was created successfully
        console.warn('Category save failed for new item', created.id)
      }
    }

    emit('created', created)
    close()
  } catch (err) {
    submitError.value = err.message ?? t('common.error')
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
// Backdrop
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
  padding: $space-4;
}

// Modal panel
.modal {
  width: min(520px, 100%);
  background-color: $color-bg-elevated;
  border: 1px solid $color-border;
  border-radius: $radius-xl;
  box-shadow: $shadow-lg;
  overflow: hidden;
}

.modal__header {
  display: flex;
  align-items: center;
  gap: $space-3;
  padding: $space-5 $space-6;
  border-bottom: 1px solid $color-border-subtle;
}

.modal__domain-icon {
  font-size: $text-xl;
  color: var(--domain-color);
  line-height: 1;
}

.modal__title {
  font-family: $font-display;
  font-size: $text-xl;
  font-weight: $font-weight-light;
  color: $color-text-primary;
  flex: 1;
}

.modal__close {
  color: $color-text-muted;
  font-size: $text-sm;
  transition: color $transition-fast;
  &:hover { color: $color-text-primary; }
}

// Body
.modal__body {
  padding: $space-6;
  display: flex;
  flex-direction: column;
  gap: $space-5;
}

.modal__row {
  display: flex;
  gap: $space-4;
}

.modal__field {
  display: flex;
  flex-direction: column;
  gap: $space-2;

  &--half { flex: 1; }
}

.modal__label {
  font-size: $text-sm;
  color: $color-text-secondary;
  font-weight: $font-weight-medium;
}

.modal__required {
  color: $color-error;
  margin-left: 2px;
}

.modal__optional {
  color: $color-text-muted;
  font-weight: $font-weight-regular;
  margin-left: $space-1;
}

.modal__input {
  background: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-md;
  padding: $space-2 $space-3;
  color: $color-text-primary;
  font-size: $text-sm;
  font-family: $font-body;
  transition: border-color $transition-fast;

  &::placeholder { color: $color-text-muted; }
  &:focus { outline: none; border-color: var(--domain-color); }
  &--error { border-color: $color-error; }

  // Remove number input spinners
  &[type="number"] {
    -moz-appearance: textfield;
    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button { display: none; }
  }
}

.modal__select {
  background: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-md;
  padding: $space-2 $space-3;
  color: $color-text-primary;
  font-size: $text-sm;
  font-family: $font-body;
  cursor: pointer;
  transition: border-color $transition-fast;
  &:focus { outline: none; border-color: var(--domain-color); }
  option { background: $color-bg-elevated; color: $color-text-primary; }
}

.modal__error {
  font-size: $text-xs;
  color: $color-error;
  margin-top: -$space-1;
}

// Rating widget inside modal
.modal__rating {
  display: flex;
  align-items: center;
  gap: $space-1;
  height: 36px; // Match input height
}

.modal__star {
  font-size: $text-lg;
  color: $color-text-muted;
  opacity: 0.4;
  transition: color $transition-fast, transform $transition-fast, opacity $transition-fast;
  line-height: 1;

  &--filled {
    color: $color-accent;
    opacity: 1;
  }

  &--hovered {
    transform: scale(1.2);
  }

  &:hover {
    opacity: 1;
    color: $color-accent;
    transform: scale(1.2);
  }
}

.modal__rating-clear {
  font-size: $text-xs;
  color: $color-text-muted;
  margin-left: $space-1;
  transition: color $transition-fast;
  &:hover { color: $color-text-primary; }
}

// Footer
.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: $space-3;
  padding: $space-4 $space-6;
  border-top: 1px solid $color-border-subtle;
}

.modal__btn {
  padding: $space-2 $space-6;
  border-radius: $radius-md;
  font-size: $text-sm;
  font-weight: $font-weight-medium;
  transition: opacity $transition-fast, background-color $transition-fast;

  &--cancel {
    color: $color-text-muted;
    border: 1px solid $color-border-subtle;
    &:hover { color: $color-text-primary; border-color: $color-border; }
  }

  &--submit {
    background-color: var(--domain-color);
    color: $color-bg;
    opacity: 0.9;
    &:hover:not(:disabled) { opacity: 1; }
    &:disabled { opacity: 0.3; cursor: not-allowed; }
  }
}

.modal__submit-error {
  padding: 0 $space-6 $space-4;
  font-size: $text-xs;
  color: $color-error;
  text-align: center;
}

// Transition
.modal-enter-active,
.modal-leave-active {
  transition: opacity $transition-normal;
  .modal {
    transition: transform $transition-normal, opacity $transition-normal;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  .modal {
    transform: translateY(12px);
    opacity: 0;
  }
}
</style>
