<template>
  <div class="insights-view">
    <header class="insights-view__header">
      <h1 class="insights-view__title">{{ $t("insights.title") }}</h1>
      <p class="insights-view__subtitle">{{ $t("insights.subtitle") }}</p>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="insights-view__loading">
      <p>{{ $t("common.loading") }}</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="insights-view__error">
      <p>{{ $t("common.error") }}</p>
      <button @click="loadData">{{ $t("common.retry") }}</button>
    </div>

    <template v-else>
      <!-- Row 1: KPI strip -->
      <section class="insights-view__kpis">
        <div
          v-for="domain in DOMAINS"
          :key="domain.key"
          class="kpi-card"
          :style="{ '--domain-color': domain.color }"
        >
          <span class="kpi-card__icon">{{ domain.icon }}</span>
          <span class="kpi-card__value">{{ counts[domain.key] ?? 0 }}</span>
          <span class="kpi-card__label">{{ $t(domain.labelKey) }}</span>
          <span v-if="avgRatings[domain.key]" class="kpi-card__avg">
            {{ avgRatings[domain.key] }} ★
          </span>
        </div>
      </section>

      <!-- Row 2: Donut + Rating distribution -->
      <section class="insights-view__row">
        <div class="insights-card">
          <h2 class="insights-card__title">
            {{ $t("insights.domain_breakdown") }}
          </h2>
          <DomainBreakdownChart :counts="counts" />
        </div>

        <div class="insights-card insights-card--wide">
          <h2 class="insights-card__title">
            {{ $t("insights.rating_distribution") }}
          </h2>
          <RatingDistributionChart :domain-stats="profile.domainStats" />
        </div>
      </section>

      <!-- Row 3: Decades -->
      <section class="insights-view__row">
        <div class="insights-card insights-card--full">
          <h2 class="insights-card__title">{{ $t("insights.decades") }}</h2>
          <DecadesChart :decades="profile.decades" />
        </div>
      </section>

      <!-- Row 4: Top creators -->
      <section class="insights-view__row">
        <div class="insights-card insights-card--full">
          <h2 class="insights-card__title">
            {{ $t("insights.top_creators") }}
          </h2>
          <TopCreatorsChart :creators="profile.topCreators" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { fetchCounts, fetchTasteProfile, parseTasteProfile } from "@/api/stats";
import { DOMAINS } from "@/config/domains";
import DomainBreakdownChart from "@/components/charts/DomainBreakdownChart.vue";
import RatingDistributionChart from "@/components/charts/RatingDistributionChart.vue";
import DecadesChart from "@/components/charts/DecadesChart.vue";
import TopCreatorsChart from "@/components/charts/TopCreatorsChart.vue";

const loading = ref(true);
const error = ref(null);
const counts = ref({});
const profile = ref({
  domainStats: [],
  topGenres: [],
  topCreators: [],
  decades: [],
});

/**
 * Build a lookup of average ratings by domain from domain_stats rows.
 * Returns { music: '4.2', book: '3.8', ... }
 */
const avgRatings = computed(() => {
  const result = {};
  for (const row of profile.value.domainStats) {
    const d =
      typeof row.details === "string"
        ? JSON.parse(row.details)
        : (row.details ?? {});
    if (d.avg_rating != null) {
      result[row.dimension] = Number(d.avg_rating).toFixed(1);
    }
  }
  return result;
});

async function loadData() {
  loading.value = true;
  error.value = null;

  try {
    const [countsData, profileData] = await Promise.all([
      fetchCounts(),
      fetchTasteProfile(),
    ]);
    counts.value = countsData;
    profile.value = parseTasteProfile(profileData);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.insights-view {
  padding-top: $space-2;
}

// Header
.insights-view__header {
  margin-bottom: $space-10;
}

.insights-view__title {
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

.insights-view__subtitle {
  font-size: $text-base;
  color: $color-text-muted;
  font-weight: $font-weight-light;
}

.insights-view__loading,
.insights-view__error {
  padding: $space-16;
  text-align: center;
  color: $color-text-secondary;
}

// KPI strip
.insights-view__kpis {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: $space-3;
  margin-bottom: $space-8;

  @media (max-width: #{$bp-lg - 1px}) {
    grid-template-columns: repeat(3, 1fr);
  }

  @media (max-width: #{$bp-sm - 1px}) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.kpi-card {
  background-color: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-lg;
  padding: $space-4;
  display: flex;
  flex-direction: column;
  gap: $space-1;
  transition: border-color $transition-fast;

  &:hover {
    border-color: var(--domain-color);
  }
}

.kpi-card__icon {
  font-size: $text-lg;
  color: var(--domain-color);
  opacity: 0.8;
}

.kpi-card__value {
  font-family: $font-display;
  font-size: $text-3xl;
  font-weight: $font-weight-light;
  color: var(--domain-color);
  line-height: 1;
  letter-spacing: -0.02em;
}

.kpi-card__label {
  font-size: $text-xs;
  color: $color-text-muted;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.kpi-card__avg {
  font-size: $text-xs;
  color: $color-accent;
  margin-top: $space-1;
}

// Chart layout
.insights-view__row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: $space-6;
  margin-bottom: $space-6;

  @media (max-width: #{$bp-lg - 1px}) {
    grid-template-columns: 1fr;
  }
}

.insights-card {
  background-color: $color-bg-card;
  border: 1px solid $color-border-subtle;
  border-radius: $radius-xl;
  padding: $space-6;

  &--wide {
    // Takes 2fr in the grid — no extra style needed
  }

  &--full {
    grid-column: 1 / -1;
  }
}

.insights-card__title {
  font-family: $font-display;
  font-size: $text-lg;
  font-weight: $font-weight-light;
  color: $color-text-secondary;
  margin-bottom: $space-6;
  letter-spacing: 0.02em;
}
</style>
