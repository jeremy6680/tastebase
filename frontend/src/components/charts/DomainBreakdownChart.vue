<template>
  <div class="chart-wrapper">
    <Doughnut :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Doughnut } from "vue-chartjs";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { DOMAINS } from "@/config/domains";

ChartJS.register(ArcElement, Tooltip, Legend);

const props = defineProps({
  /** Object keyed by domain name with item counts. e.g. { music: 42, book: 18 } */
  counts: {
    type: Object,
    required: true,
  },
});

/** Build Chart.js dataset from domain counts and DOMAINS color config. */
const chartData = computed(() => {
  const labels = DOMAINS.map((d) => d.key);
  const data = DOMAINS.map((d) => props.counts[d.key] ?? 0);
  const colors = DOMAINS.map((d) => d.color);

  return {
    labels,
    datasets: [
      {
        data,
        backgroundColor: colors.map((c) => c + "cc"), // 80% opacity
        borderColor: colors,
        borderWidth: 2,
        hoverOffset: 8,
      },
    ],
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: true,
  cutout: "65%",
  plugins: {
    legend: {
      position: "right",
      labels: {
        color: "#8a8780",
        font: { size: 12 },
        padding: 16,
        boxWidth: 12,
        boxHeight: 12,
      },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => ` ${ctx.parsed} items`,
      },
    },
  },
};
</script>

<style lang="scss" scoped>
.chart-wrapper {
  max-width: 420px;
  margin: 0 auto;
}
</style>
