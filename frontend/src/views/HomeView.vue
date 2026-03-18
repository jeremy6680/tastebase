<template>
  <div class="home-view">
    <!-- Page header -->
    <header class="home-view__header">
      <h1 class="home-view__title">
        {{ $t("home.title") }}
      </h1>
      <p class="home-view__subtitle">{{ $t("home.subtitle") }}</p>
    </header>

    <!-- Domain cards grid -->
    <section class="home-view__domains" aria-label="Domains">
      <!-- Loading state -->
      <template v-if="loading">
        <div v-for="n in 6" :key="n" class="domain-card domain-card--skeleton">
          <div class="skeleton skeleton--icon" />
          <div class="skeleton skeleton--title" />
          <div class="skeleton skeleton--count" />
        </div>
      </template>

      <!-- Error state -->
      <div v-else-if="error" class="home-view__error">
        <p>{{ $t("common.error") }}</p>
        <button class="home-view__retry" @click="loadData">
          {{ $t("common.retry") }}
        </button>
      </div>

      <!-- Domain cards -->
      <template v-else>
        <RouterLink
          v-for="(domain, index) in DOMAINS"
          :key="domain.key"
          :to="domain.route"
          class="domain-card"
          :style="{
            '--domain-color': domain.color,
            '--stagger-delay': `${index * 60}ms`,
          }"
        >
          <div class="domain-card__icon">{{ domain.icon }}</div>

          <div class="domain-card__body">
            <h2 class="domain-card__title">{{ $t(domain.labelKey) }}</h2>
            <div class="domain-card__count">
              <span class="domain-card__count-number">
                {{ counts[domain.key] ?? 0 }}
              </span>
              <span class="domain-card__count-label">
                {{ $t("common.items", counts[domain.key] ?? 0) }}
              </span>
            </div>
          </div>

          <!-- Rated badge -->
          <div v-if="ratedCounts[domain.key]" class="domain-card__rated">
            {{ ratedCounts[domain.key] }}
            {{ $t("common.rated", ratedCounts[domain.key]) }}
          </div>

          <!-- Decorative corner accent -->
          <div class="domain-card__accent" aria-hidden="true" />
        </RouterLink>
      </template>
    </section>

    <!-- Total items summary -->
    <div v-if="!loading && !error" class="home-view__total">
      <span class="home-view__total-number">{{ totalItems }}</span>
      <span class="home-view__total-label">
        {{ $t("home.total_items", totalItems) }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { fetchCounts } from "@/api/stats";
import { DOMAINS } from "@/config/domains";

// State
const loading = ref(true);
const error = ref(null);
const counts = ref({});
const ratedCounts = ref({});

// Total items across all domains
const totalItems = computed(() =>
  Object.values(counts.value).reduce((sum, n) => sum + (n || 0), 0),
);

/**
 * Load domain counts from the FastAPI /stats/counts endpoint.
 * The expected response shape is:
 * { music: N, book: N, manga: N, movie: N, series: N, anime: N,
 *   music_rated: N, book_rated: N, ... }
 */
async function loadData() {
  loading.value = true;
  error.value = null;

  try {
    const data = await fetchCounts();

    // Separate total counts from rated counts
    const totals = {};
    const rated = {};

    for (const [key, value] of Object.entries(data)) {
      if (key.endsWith("_rated")) {
        rated[key.replace("_rated", "")] = value;
      } else {
        totals[key] = value;
      }
    }

    counts.value = totals;
    ratedCounts.value = rated;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.home-view {
  padding-top: $space-2;
}

// Header
.home-view__header {
  margin-bottom: $space-12;
}

.home-view__title {
  font-family: $font-display;
  font-size: $text-5xl;
  font-weight: $font-weight-light;
  color: $color-text-primary;
  letter-spacing: -0.03em;
  line-height: $line-height-tight;
  margin-bottom: $space-3;

  @media (max-width: #{$bp-md - 1px}) {
    font-size: $text-3xl;
  }
}

.home-view__subtitle {
  font-size: $text-base;
  color: $color-text-muted;
  font-weight: $font-weight-light;
}

// Domain cards grid
.home-view__domains {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $space-4;
  margin-bottom: $space-10;

  @media (max-width: #{$bp-lg - 1px}) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: #{$bp-sm - 1px}) {
    grid-template-columns: 1fr;
  }
}

// Domain card
.domain-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: $space-4;
  background-color: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-xl;
  padding: $space-6;
  text-decoration: none;
  overflow: hidden;
  cursor: pointer;
  transition:
    border-color $transition-fast,
    transform $transition-fast,
    box-shadow $transition-fast;

  // Staggered entrance animation
  animation: card-enter 0.5s ease both;
  animation-delay: var(--stagger-delay, 0ms);

  &:hover {
    border-color: var(--domain-color);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);

    .domain-card__icon {
      color: var(--domain-color);
      transform: scale(1.1);
    }

    .domain-card__accent {
      opacity: 0.15;
    }
  }

  // Skeleton variant
  &--skeleton {
    pointer-events: none;
    animation: none;
    cursor: default;
  }
}

.domain-card__icon {
  font-size: $text-2xl;
  color: var(--domain-color);
  opacity: 0.7;
  transition:
    color $transition-fast,
    transform $transition-fast;
  line-height: 1;
}

.domain-card__body {
  flex: 1;
}

.domain-card__title {
  font-family: $font-display;
  font-size: $text-xl;
  font-weight: $font-weight-light;
  color: $color-text-primary;
  margin-bottom: $space-2;
}

.domain-card__count {
  display: flex;
  align-items: baseline;
  gap: $space-2;
}

.domain-card__count-number {
  font-family: $font-display;
  font-size: $text-3xl;
  font-weight: $font-weight-light;
  color: var(--domain-color);
  letter-spacing: -0.02em;
  line-height: 1;
}

.domain-card__count-label {
  font-size: $text-sm;
  color: $color-text-muted;
}

.domain-card__rated {
  font-size: $text-xs;
  color: $color-text-muted;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

// Decorative background accent (domain color blob)
.domain-card__accent {
  position: absolute;
  bottom: -20px;
  right: -20px;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background-color: var(--domain-color);
  opacity: 0.06;
  transition: opacity $transition-normal;
  pointer-events: none;
}

// Skeleton placeholders
.skeleton {
  background: linear-gradient(
    90deg,
    $color-bg-elevated 25%,
    rgba(255, 255, 255, 0.04) 50%,
    $color-bg-elevated 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: $radius-sm;

  &--icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
  }
  &--title {
    width: 60%;
    height: 20px;
    margin-bottom: $space-3;
  }
  &--count {
    width: 40%;
    height: 36px;
  }
}

// Total summary
.home-view__total {
  display: flex;
  align-items: baseline;
  gap: $space-3;
  padding-top: $space-6;
  border-top: 1px solid $color-border-subtle;
}

.home-view__total-number {
  font-family: $font-display;
  font-size: $text-4xl;
  font-weight: $font-weight-light;
  color: $color-accent;
  letter-spacing: -0.02em;
}

.home-view__total-label {
  font-size: $text-base;
  color: $color-text-muted;
}

// Error state
.home-view__error {
  grid-column: 1 / -1;
  text-align: center;
  padding: $space-12;
  color: $color-text-secondary;
}

.home-view__retry {
  margin-top: $space-4;
  padding: $space-2 $space-6;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  color: $color-text-secondary;
  font-size: $text-sm;
  transition:
    border-color $transition-fast,
    color $transition-fast;

  &:hover {
    border-color: $color-accent;
    color: $color-accent;
  }
}

// Entrance animation
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
