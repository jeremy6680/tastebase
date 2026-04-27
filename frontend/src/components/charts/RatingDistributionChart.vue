<template>
  <div class="chart-wrapper">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Bar } from "vue-chartjs";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";
import { DOMAINS } from "@/config/domains";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const props = defineProps({
  /**
   * Array of domain_stats rows from mart_taste_profile.
   * Each row has: { dimension: 'music', details: '{"five_star":N,...}' }
   */
  domainStats: {
    type: Array,
    required: true,
  },
});

/**
 * Parse the details JSON string from a domain_stats row.
 * Returns an object with five_star, four_star, ... one_star keys.
 *
 * @param {string|Object} details - JSON string or already-parsed object
 * @returns {Object}
 */
function parseDetails(details) {
  if (!details) return {};
  if (typeof details === "string") {
    try {
      return JSON.parse(details);
    } catch {
      return {};
    }
  }
  return details;
}

/** Labels: star ratings 1–5 */
const labels = ["★1", "★2", "★3", "★4", "★5"];

/** Build one dataset per domain. */
const chartData = computed(() => {
  const datasets = props.domainStats.map((row) => {
    const domain = DOMAINS.find((d) => d.key === row.dimension);
    const d = parseDetails(row.details);
    return {
      label: row.dimension,
      data: [
        d.one_star ?? 0,
        d.two_star ?? 0,
        d.three_star ?? 0,
        d.four_star ?? 0,
        d.five_star ?? 0,
      ],
      backgroundColor: (domain?.color ?? "#8a8780") + "bb",
      borderColor: domain?.color ?? "#8a8780",
      borderWidth: 1,
      borderRadius: 4,
    };
  });

  return { labels, datasets };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "top",
      labels: {
        color: "#8a8780",
        font: { size: 12 },
        padding: 12,
        boxWidth: 12,
      },
    },
  },
  scales: {
    x: {
      ticks: { color: "#8a8780" },
      grid: { color: "rgba(255,255,255,0.04)" },
    },
    y: {
      ticks: { color: "#8a8780", precision: 0 },
      grid: { color: "rgba(255,255,255,0.06)" },
      beginAtZero: true,
    },
  },
};
</script>

<style lang="scss" scoped>
.chart-wrapper {
  height: 320px;
}
</style>
