<template>
  <!-- Backdrop -->
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="modelValue"
        class="upload-modal-backdrop"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('upload.title')"
        @click.self="close"
        @keydown.esc="close"
      >
        <div class="upload-modal">
          <!-- Header -->
          <div class="upload-modal__header">
            <h2 class="upload-modal__title">{{ $t('upload.title') }}</h2>
            <button
              class="upload-modal__close"
              :aria-label="$t('common.cancel')"
              @click="close"
            >
              ✕
            </button>
          </div>

          <!-- Step 1: source + file selection -->
          <div v-if="phase === 'idle'" class="upload-modal__body">
            <!-- Source select -->
            <div class="upload-modal__field">
              <label class="upload-modal__label" for="upload-source">
                {{ $t('upload.source_label') }}
              </label>

              <!-- Loading sources -->
              <div v-if="loadingSources" class="upload-modal__sources-loading">
                {{ $t('common.loading') }}
              </div>

              <div v-else class="upload-modal__sources">
                <button
                  v-for="src in sources"
                  :key="src.key"
                  class="upload-modal__source-btn"
                  :class="{
                    'upload-modal__source-btn--active': selectedSource === src.key,
                    'upload-modal__source-btn--present': src.present,
                  }"
                  @click="selectedSource = src.key"
                >
                  <span class="upload-modal__source-name">{{ src.label }}</span>
                  <span class="upload-modal__source-domain">{{ src.domain }}</span>
                  <span
                    v-if="src.present"
                    class="upload-modal__source-badge"
                    :title="$t('upload.file_present')"
                  >✓</span>
                </button>
              </div>
            </div>

            <!-- Drop zone -->
            <div
              class="upload-modal__field"
              :class="{ 'upload-modal__field--disabled': !selectedSource }"
            >
              <label class="upload-modal__label">{{ $t('upload.file_label') }}</label>
              <div
                class="upload-modal__dropzone"
                :class="{
                  'upload-modal__dropzone--active': isDragging,
                  'upload-modal__dropzone--filled': selectedFile,
                  'upload-modal__dropzone--disabled': !selectedSource,
                }"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="onDrop"
                @click="selectedSource && $refs.fileInput.click()"
              >
                <input
                  ref="fileInput"
                  type="file"
                  accept=".csv,text/csv,application/csv"
                  class="upload-modal__file-input"
                  @change="onFileChange"
                />

                <template v-if="selectedFile">
                  <span class="upload-modal__dropzone-icon">📄</span>
                  <span class="upload-modal__dropzone-filename">{{ selectedFile.name }}</span>
                  <span class="upload-modal__dropzone-size">{{ formatSize(selectedFile.size) }}</span>
                </template>
                <template v-else>
                  <span class="upload-modal__dropzone-icon">⬆</span>
                  <span class="upload-modal__dropzone-hint">
                    {{ selectedSource ? $t('upload.drop_hint') : $t('upload.select_source_first') }}
                  </span>
                </template>
              </div>
            </div>

            <!-- Error -->
            <p v-if="validationError" class="upload-modal__validation-error">
              {{ validationError }}
            </p>

            <!-- Actions -->
            <div class="upload-modal__actions">
              <button class="upload-modal__btn upload-modal__btn--ghost" @click="close">
                {{ $t('common.cancel') }}
              </button>
              <button
                class="upload-modal__btn upload-modal__btn--primary"
                :disabled="!canSubmit"
                @click="submit"
              >
                {{ $t('upload.submit') }}
              </button>
            </div>
          </div>

          <!-- Step 2: uploading / running pipeline -->
          <div v-else-if="phase === 'uploading'" class="upload-modal__body upload-modal__body--center">
            <div class="upload-modal__spinner" aria-hidden="true" />
            <p class="upload-modal__status-label">{{ $t('upload.uploading') }}</p>
            <div v-if="uploadProgress > 0" class="upload-modal__progress">
              <div
                class="upload-modal__progress-bar"
                :style="{ width: `${uploadProgress}%` }"
              />
            </div>
          </div>

          <!-- Step 3: result -->
          <div v-else-if="phase === 'done'" class="upload-modal__body">
            <!-- Success / partial failure banner -->
            <div
              class="upload-modal__result-banner"
              :class="{
                'upload-modal__result-banner--success': result.ingestion.status === 'ok',
                'upload-modal__result-banner--warning': result.ingestion.status !== 'ok',
              }"
            >
              <span class="upload-modal__result-icon">
                {{ result.ingestion.status === 'ok' ? '✓' : '⚠' }}
              </span>
              <span>
                {{
                  result.ingestion.status === 'ok'
                    ? $t('upload.success', { filename: result.filename })
                    : $t('upload.partial_failure')
                }}
              </span>
            </div>

            <!-- Pipeline logs (collapsible) -->
            <details class="upload-modal__logs">
              <summary class="upload-modal__logs-summary">{{ $t('upload.show_logs') }}</summary>
              <pre class="upload-modal__logs-content">{{ logsText }}</pre>
            </details>

            <div class="upload-modal__actions">
              <button class="upload-modal__btn upload-modal__btn--ghost" @click="reset">
                {{ $t('upload.upload_another') }}
              </button>
              <button class="upload-modal__btn upload-modal__btn--primary" @click="close">
                {{ $t('common.done') }}
              </button>
            </div>
          </div>

          <!-- Step 4: error -->
          <div v-else-if="phase === 'error'" class="upload-modal__body upload-modal__body--center">
            <span class="upload-modal__error-icon">✕</span>
            <p class="upload-modal__error-message">{{ errorMessage }}</p>
            <div class="upload-modal__actions">
              <button class="upload-modal__btn upload-modal__btn--ghost" @click="reset">
                {{ $t('common.retry') }}
              </button>
              <button class="upload-modal__btn upload-modal__btn--primary" @click="close">
                {{ $t('common.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { fetchSources, uploadCsv } from '@/api/ingestion'

// ---------------------------------------------------------------------------
// Props / emits
// ---------------------------------------------------------------------------

const props = defineProps({
  /** Controls visibility — use v-model */
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'ingestion-complete'])

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const phase = ref('idle') // idle | uploading | done | error

const sources = ref([])
const loadingSources = ref(false)

const selectedSource = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const validationError = ref(null)

const uploadProgress = ref(0)
const result = ref(null)
const errorMessage = ref(null)

const fileInput = ref(null)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const canSubmit = computed(
  () => selectedSource.value !== null && selectedFile.value !== null
)

const logsText = computed(() => {
  if (!result.value) return ''
  const r = result.value.ingestion
  return [
    '=== Ingestion ===',
    r.ingestion_stdout || '(no output)',
    '',
    '=== dbt run ===',
    r.dbt_stdout || '(no output)',
  ].join('\n')
})

// ---------------------------------------------------------------------------
// Watchers
// ---------------------------------------------------------------------------

// Load sources when modal opens
watch(
  () => props.modelValue,
  (open) => {
    if (open && sources.value.length === 0) {
      loadSourceList()
    }
  }
)

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

async function loadSourceList() {
  loadingSources.value = true
  try {
    const data = await fetchSources()
    sources.value = data.sources ?? data
  } catch {
    // Non-blocking: user can still see the source buttons from SOURCES constant
    sources.value = []
  } finally {
    loadingSources.value = false
  }
}

function onDrop(event) {
  isDragging.value = false
  if (!selectedSource.value) return
  const file = event.dataTransfer.files[0]
  if (file) applyFile(file)
}

function onFileChange(event) {
  const file = event.target.files[0]
  if (file) applyFile(file)
}

function applyFile(file) {
  validationError.value = null
  // Basic client-side CSV check — content-type validation is done server-side too
  if (!file.name.toLowerCase().endsWith('.csv')) {
    validationError.value = 'Le fichier doit être un CSV (.csv)'
    return
  }
  selectedFile.value = file
}

async function submit() {
  if (!canSubmit.value) return
  validationError.value = null
  phase.value = 'uploading'
  uploadProgress.value = 0

  try {
    const data = await uploadCsv(
      selectedSource.value,
      selectedFile.value,
      (event) => {
        if (event.lengthComputable) {
          uploadProgress.value = Math.round((event.loaded / event.total) * 100)
        }
      }
    )
    result.value = data
    phase.value = 'done'
    emit('ingestion-complete', data)
  } catch (err) {
    errorMessage.value =
      err?.response?.data?.detail ?? err?.message ?? 'Une erreur inattendue est survenue.'
    phase.value = 'error'
  }
}

function reset() {
  phase.value = 'idle'
  selectedFile.value = null
  validationError.value = null
  uploadProgress.value = 0
  result.value = null
  errorMessage.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function close() {
  emit('update:modelValue', false)
  // Delay reset so the closing animation finishes
  setTimeout(reset, 300)
}

/**
 * Format a byte count as a human-readable string.
 * @param {number} bytes
 * @returns {string}
 */
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<style lang="scss" scoped>
@use 'sass:color';
// ---------------------------------------------------------------------------
// Backdrop
// ---------------------------------------------------------------------------

.upload-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: $space-4;
}

// ---------------------------------------------------------------------------
// Modal container
// ---------------------------------------------------------------------------

.upload-modal {
  background: $color-bg-elevated;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-xl;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

.upload-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $space-6;
  border-bottom: 1px solid $color-border-subtle;
  flex-shrink: 0;
}

.upload-modal__title {
  font-family: $font-display;
  font-size: $text-xl;
  font-weight: $font-weight-light;
  color: $color-text-primary;
}

.upload-modal__close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-md;
  color: $color-text-muted;
  font-size: $text-sm;
  transition: color $transition-fast, background $transition-fast;

  &:hover {
    color: $color-text-primary;
    background: rgba(255, 255, 255, 0.06);
  }
}

// ---------------------------------------------------------------------------
// Body
// ---------------------------------------------------------------------------

.upload-modal__body {
  padding: $space-6;
  display: flex;
  flex-direction: column;
  gap: $space-5;

  &--center {
    align-items: center;
    text-align: center;
    padding: $space-12 $space-6;
  }
}

// ---------------------------------------------------------------------------
// Fields
// ---------------------------------------------------------------------------

.upload-modal__field {
  display: flex;
  flex-direction: column;
  gap: $space-3;

  &--disabled {
    opacity: 0.5;
    pointer-events: none;
  }
}

.upload-modal__label {
  font-size: $text-sm;
  font-weight: $font-weight-medium;
  color: $color-text-secondary;
  letter-spacing: 0.03em;
}

// ---------------------------------------------------------------------------
// Source buttons
// ---------------------------------------------------------------------------

.upload-modal__sources-loading {
  font-size: $text-sm;
  color: $color-text-muted;
}

.upload-modal__sources {
  display: flex;
  flex-wrap: wrap;
  gap: $space-2;
}

.upload-modal__source-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: $space-3 $space-4;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-md;
  background: $color-bg-card;
  cursor: pointer;
  transition: border-color $transition-fast, background $transition-fast;
  min-width: 120px;

  &:hover {
    border-color: $color-border;
    background: rgba(255, 255, 255, 0.04);
  }

  &--active {
    border-color: $color-accent;
    background: rgba($color-accent, 0.08);
  }
}

.upload-modal__source-name {
  font-size: $text-sm;
  font-weight: $font-weight-medium;
  color: $color-text-primary;
}

.upload-modal__source-domain {
  font-size: $text-xs;
  color: $color-text-muted;
  margin-top: $space-1;
}

.upload-modal__source-badge {
  position: absolute;
  top: $space-2;
  right: $space-2;
  font-size: $text-xs;
  color: $color-accent;
  font-weight: $font-weight-semi;
}

// ---------------------------------------------------------------------------
// Drop zone
// ---------------------------------------------------------------------------

.upload-modal__dropzone {
  border: 2px dashed $color-border-subtle;
  border-radius: $radius-lg;
  padding: $space-10 $space-6;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $space-2;
  cursor: pointer;
  transition: border-color $transition-fast, background $transition-fast;
  text-align: center;

  &:hover:not(&--disabled) {
    border-color: $color-border;
    background: rgba(255, 255, 255, 0.02);
  }

  &--active {
    border-color: $color-accent;
    background: rgba($color-accent, 0.05);
  }

  &--filled {
    border-color: $color-accent;
    border-style: solid;
    background: rgba($color-accent, 0.06);
  }

  &--disabled {
    cursor: default;
    opacity: 0.4;
  }
}

.upload-modal__file-input {
  display: none;
}

.upload-modal__dropzone-icon {
  font-size: $text-2xl;
  color: $color-text-muted;
  line-height: 1;
}

.upload-modal__dropzone-hint {
  font-size: $text-sm;
  color: $color-text-muted;
}

.upload-modal__dropzone-filename {
  font-size: $text-sm;
  color: $color-text-primary;
  font-weight: $font-weight-medium;
  word-break: break-all;
}

.upload-modal__dropzone-size {
  font-size: $text-xs;
  color: $color-text-muted;
}

// ---------------------------------------------------------------------------
// Validation error
// ---------------------------------------------------------------------------

.upload-modal__validation-error {
  font-size: $text-sm;
  color: #e05c5c;
  margin-top: -$space-2;
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

.upload-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: $space-3;
  margin-top: $space-2;
}

.upload-modal__btn {
  padding: $space-2 $space-5;
  border-radius: $radius-md;
  font-size: $text-sm;
  font-weight: $font-weight-medium;
  transition: all $transition-fast;
  cursor: pointer;

  &--ghost {
    border: 1px solid $color-border;
    color: $color-text-secondary;

    &:hover {
      border-color: $color-border-subtle;
      color: $color-text-primary;
    }
  }

  &--primary {
    background: $color-accent;
    color: #000;
    border: 1px solid $color-accent;

    &:hover:not(:disabled) {
      background: color.adjust($color-accent, $lightness: 8%);
    }

    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }
}

// ---------------------------------------------------------------------------
// Uploading phase
// ---------------------------------------------------------------------------

.upload-modal__spinner {
  width: 40px;
  height: 40px;
  border: 3px solid $color-border-subtle;
  border-top-color: $color-accent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: $space-4;
}

.upload-modal__status-label {
  font-size: $text-sm;
  color: $color-text-secondary;
}

.upload-modal__progress {
  width: 200px;
  height: 4px;
  background: $color-border-subtle;
  border-radius: $radius-sm;
  overflow: hidden;
  margin-top: $space-4;
}

.upload-modal__progress-bar {
  height: 100%;
  background: $color-accent;
  border-radius: $radius-sm;
  transition: width 0.2s ease;
}

// ---------------------------------------------------------------------------
// Result phase
// ---------------------------------------------------------------------------

.upload-modal__result-banner {
  display: flex;
  align-items: center;
  gap: $space-3;
  padding: $space-4;
  border-radius: $radius-md;
  font-size: $text-sm;
  font-weight: $font-weight-medium;

  &--success {
    background: rgba(80, 200, 120, 0.12);
    border: 1px solid rgba(80, 200, 120, 0.3);
    color: #6ddfaa;
  }

  &--warning {
    background: rgba(255, 180, 0, 0.1);
    border: 1px solid rgba(255, 180, 0, 0.3);
    color: #ffd060;
  }
}

.upload-modal__result-icon {
  font-size: $text-lg;
  flex-shrink: 0;
}

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------

.upload-modal__logs {
  border: 1px solid $color-border-subtle;
  border-radius: $radius-md;
  overflow: hidden;
}

.upload-modal__logs-summary {
  padding: $space-3 $space-4;
  font-size: $text-sm;
  color: $color-text-muted;
  cursor: pointer;
  user-select: none;

  &:hover {
    color: $color-text-secondary;
  }
}

.upload-modal__logs-content {
  padding: $space-4;
  font-size: $text-xs;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: $color-text-muted;
  background: $color-bg;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow-y: auto;
  border-top: 1px solid $color-border-subtle;
}

// ---------------------------------------------------------------------------
// Error phase
// ---------------------------------------------------------------------------

.upload-modal__error-icon {
  font-size: $text-3xl;
  color: #e05c5c;
  display: block;
  margin-bottom: $space-2;
}

.upload-modal__error-message {
  font-size: $text-sm;
  color: $color-text-secondary;
  max-width: 320px;
}

// ---------------------------------------------------------------------------
// Animations
// ---------------------------------------------------------------------------

.modal-enter-active,
.modal-leave-active {
  transition: opacity $transition-normal;

  .upload-modal {
    transition: transform $transition-normal;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;

  .upload-modal {
    transform: translateY(16px) scale(0.98);
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
