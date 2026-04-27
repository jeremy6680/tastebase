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
   * Array of decade rows from mart_taste_profile.
   * Each row: { dimension: '1990s', sub_dimension: 'music', value_int: 12 }
   */
  decades: {
    type: Array,
    required: true,
  },
});

/** Collect sorted unique decade labels. */
const decadeLabels = computed(() => {
  const set = new Set(props.decades.map((r) => r.dimension));
  return [...set].sort();
});

/** Build one stacked dataset per domain. */
const chartData = computed(() => {
  const datasets = DOMAINS.map((domain) => {
    const data = decadeLabels.value.map((decade) => {
      const row = props.decades.find(
        (r) => r.dimension === decade && r.sub_dimension === domain.key,
      );
      return row?.value_int ?? 0;
    });
    return {
      label: domain.key,
      data,
      backgroundColor: domain.color + "bb",
      borderColor: domain.color,
      borderWidth: 1,
      borderRadius: 2,
    };
  });

  return { labels: decadeLabels.value, datasets };
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
      stacked: true,
      ticks: { color: "#8a8780" },
      grid: { color: "rgba(255,255,255,0.04)" },
    },
    y: {
      stacked: true,
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
