<template>
  <div class="chart-wrapper">
    <!-- Domain filter -->
    <div class="top-creators__filter">
      <button
        v-for="opt in filterOptions"
        :key="opt.value"
        class="top-creators__filter-btn"
        :class="{
          'top-creators__filter-btn--active': activeDomain === opt.value,
        }"
        @click="activeDomain = opt.value"
      >
        {{ opt.label }}
      </button>
    </div>
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Bar } from "vue-chartjs";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
} from "chart.js";
import { DOMAINS } from "@/config/domains";
import { useI18n } from "vue-i18n";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip);

const { t } = useI18n();

const props = defineProps({
  /**
   * Array of top_creator rows from mart_taste_profile.
   * Each row: { dimension: 'Artist Name', sub_dimension: 'music', value_int: 5, value_float: 4.2 }
   */
  creators: {
    type: Array,
    required: true,
  },
});

/** Currently selected domain filter — null means all domains. */
const activeDomain = ref(null);

/** Filter button options: All + each domain. */
const filterOptions = computed(() => [
  { value: null, label: t("common.all") },
  ...DOMAINS.map((d) => ({ value: d.key, label: t(d.labelKey) })),
]);

/** Filtered + limited creator rows. */
const filteredCreators = computed(() => {
  const rows = activeDomain.value
    ? props.creators.filter((r) => r.sub_dimension === activeDomain.value)
    : props.creators;
  // Show top 15 for legibility
  return rows.slice(0, 15);
});

/** Active domain color or gold accent. */
const activeColor = computed(() => {
  if (!activeDomain.value) return "#c9a96e";
  return DOMAINS.find((d) => d.key === activeDomain.value)?.color ?? "#c9a96e";
});

const chartData = computed(() => ({
  labels: filteredCreators.value.map((r) => r.dimension),
  datasets: [
    {
      label: t("insights.items_count"),
      data: filteredCreators.value.map((r) => r.value_int),
      backgroundColor: activeColor.value + "bb",
      borderColor: activeColor.value,
      borderWidth: 1,
      borderRadius: 4,
    },
  ],
}));

const chartOptions = computed(() => ({
  indexAxis: "y", // horizontal bar chart
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        afterLabel: (ctx) => {
          const row = filteredCreators.value[ctx.dataIndex];
          if (row?.value_float) return ` avg ${row.value_float} ★`;
          return "";
        },
      },
    },
  },
  scales: {
    x: {
      ticks: { color: "#8a8780", precision: 0 },
      grid: { color: "rgba(255,255,255,0.06)" },
      beginAtZero: true,
    },
    y: {
      ticks: { color: "#f0ede8", font: { size: 12 } },
      grid: { display: false },
    },
  },
}));
</script>

<style lang="scss" scoped>
.chart-wrapper {
  height: 480px;
}

.top-creators__filter {
  display: flex;
  flex-wrap: wrap;
  gap: $space-2;
  margin-bottom: $space-4;
}

.top-creators__filter-btn {
  padding: $space-1 $space-3;
  border-radius: $radius-md;
  border: 1px solid $color-border;
  color: $color-text-secondary;
  font-size: $text-xs;
  transition: all $transition-fast;
  cursor: pointer;
  background: none;
  font-family: inherit;

  &:hover {
    border-color: $color-accent;
    color: $color-text-primary;
  }

  &--active {
    border-color: $color-accent;
    color: $color-accent;
    background-color: $color-accent-dim;
  }
}
</style>
