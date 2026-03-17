<template>
  <div class="app-shell">
    <!-- Sidebar navigation -->
    <AppSidebar />

    <!-- Main content area -->
    <main class="app-main" role="main">
      <div class="content-container">
        <!-- Route transitions -->
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="$route.path" />
          </Transition>
        </RouterView>
      </div>
    </main>
  </div>
</template>

<script setup>
import AppSidebar from "@/components/AppSidebar.vue";
</script>

<style lang="scss">
// Global styles are imported in main.js via main.scss
// Component-scoped styles are in each .vue file
</style>
