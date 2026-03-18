<template>
  <div class="domain-view" :style="{ '--domain-color': domain.color }">
    <header class="domain-view__header">
      <div class="domain-view__icon">{{ domain.icon }}</div>
      <div>
        <h1 class="domain-view__title">{{ $t(domain.labelKey) }}</h1>
        <p class="domain-view__coming-soon">
          Browse, filter and rate — coming soon.
        </p>
      </div>
    </header>

    <!-- Placeholder content area -->
    <div class="domain-view__placeholder">
      <p class="domain-view__placeholder-text">
        Cette vue sera développée dans l'étape suivante.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { DOMAINS } from "@/config/domains";

const route = useRoute();

// Resolve domain config from route meta
const domain = computed(() => {
  const domainKey = route.meta.domain;
  return DOMAINS.find((d) => d.key === domainKey) || DOMAINS[0];
});
</script>

<style lang="scss" scoped>
.domain-view {
  padding-top: $space-2;
}

.domain-view__header {
  display: flex;
  align-items: center;
  gap: $space-6;
  margin-bottom: $space-12;
}

.domain-view__icon {
  font-size: 3rem;
  color: var(--domain-color);
  line-height: 1;
  flex-shrink: 0;
}

.domain-view__title {
  font-family: $font-display;
  font-size: $text-5xl;
  font-weight: $font-weight-light;
  color: $color-text-primary;
  letter-spacing: -0.03em;
  line-height: $line-height-tight;

  @media (max-width: #{$bp-md - 1px}) {
    font-size: $text-3xl;
  }
}

.domain-view__coming-soon {
  font-size: $text-sm;
  color: $color-text-muted;
  margin-top: $space-2;
}

.domain-view__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  border: 1px dashed $color-border;
  border-radius: $radius-xl;
  background-color: rgba(255, 255, 255, 0.01);
}

.domain-view__placeholder-text {
  font-size: $text-sm;
  color: $color-text-muted;
  font-style: italic;
}
</style>
